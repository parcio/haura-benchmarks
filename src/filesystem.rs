///!
use betree_perf::*;
use betree_storage_stack::StoragePreference;
use rand::{Rng, RngCore, distributions::{Slice, DistIter}, thread_rng};
use std::{error::Error, io::Write, ops::Range};

fn pref(foo: u8, space: &mut Vec<u64>, size: u64) -> StoragePreference {
    match foo {
        0 if space[0] > size => {
            space[0] -= size;
            StoragePreference::FASTEST
        }
        1 if space[1] > size => {
            space[1] -= size;
            StoragePreference::FAST
        }
        2 if space[2] > size => {
            space[2] -= size;
            StoragePreference::SLOW
        }
        3.. => panic!(),
        _ => pref(foo + 1, space, size)
    }
}

pub fn run(mut client: Client) -> Result<(), Box<dyn Error>> {
    const SMALL: Range<u64> = (1 * 1024)..(256 * 1024);
    const MEDIUM: Range<u64> = (1 * 1024 * 1024)..(200 * 1024 * 1024);
    const LARGE: Range<u64> = (200 * 1024 * 1024)..(2 * 1024 * 1024 * 1024);
    const SIZES: [Range<u64>; 3] = [SMALL, MEDIUM, LARGE];
    // barely, seldom, often
    const AMOUNT: [usize; 3] = [2000, 300, 20];
    const PROBS: [f64; 3] = [0.01, 0.1, 0.6];

    // small, medium, large
    const DISTRIBUTION: [f32; 3] = [0.9, 0.09, 0.01];
    const TIERS: Range<u8> = 0..3;

    let mut space = client
        .database
        .read()
        .free_space_tier()
        .iter()
        .map(|tier| tier.free.to_bytes())
        .collect::<Vec<u64>>();

    println!("running filesystem");
    println!("initialize state");

    let mut groups = vec![];
    let mut counter: u64 = 1;
    for num_objs in AMOUNT.iter() {
        groups.push(vec![]);
        let objs = groups.last_mut().unwrap();
        for size_grp in 0..3 {
            for _ in 0..(*num_objs as f32 * DISTRIBUTION[size_grp]) as usize {
                let size = client.rng.gen_range(SIZES[size_grp].clone());
                let pref = pref(client.rng.gen_range(TIERS), &mut space, size);
                let key = format!("key{counter}").into_bytes();
                let (obj, _info) = client
                    .object_store
                    .open_or_create_object_with_pref(&key, pref)?;
                objs.push(key);
                counter += 1;
                let mut cursor = obj.cursor_with_pref(pref);
                with_random_bytes(&mut client.rng, size, 8 * 1024 * 1024, |b| {
                    cursor.write_all(b)
                })?;
            }
        }
    }

    println!("sync db");
    client.sync().expect("Failed to sync database");

    println!("start reading");
    let mut buf = vec![0; 2 * 1024 * 1024 * 1024];
    let mut samplers: Vec<DistIter<_,_,_>> = groups.iter().map(|ob| thread_rng().sample_iter(Slice::new(&ob).unwrap())).collect();
    for _ in 0..10000 {
        for (id, prob) in PROBS.iter().enumerate() {
            if client.rng.gen_bool(*prob) {
                let obj = samplers[id].next().unwrap();
                let obj = client
                    .object_store
                    .open_object(obj)?.unwrap();
                obj.read_at(&mut buf, 0).map_err(|e| e.1)?;
            }
        }
    }

    Ok(())
}
