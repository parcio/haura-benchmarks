///!
use betree_perf::*;
use betree_storage_stack::StoragePreference;
use betree_storage_stack::vdev::Block;
use rand::{Rng, distributions::{Slice, DistIter}, thread_rng};
use std::{error::Error, io::Write, ops::Range};

fn pref(foo: u8, size: Block<u64>, client: &Client) -> StoragePreference {
   let space = client.database.read().free_space_tier();
   match foo {
       0 if Block(space[0].free.0 - size.0) > Block((space[0].total.0 as f64 * 0.2) as u64) => {
           StoragePreference::FASTEST
       }
       1 if Block(space[1].free.0 - size.0) > Block((space[1].total.0 as f64 * 0.2) as u64) => {
           StoragePreference::FAST
       }
       2 if Block(space[2].free.0 - size.0) > Block((space[2].total.0 as f64 * 0.2) as u64) => {
           StoragePreference::SLOW
       }
       3.. => panic!(),
       _ => pref(foo + 1, size, client)
   }
}

pub fn run(mut client: Client) -> Result<(), Box<dyn Error>> {
    // barely, seldom, often
    const PROBS: [f64; 3] = [0.01, 0.2, 0.9];

    // LANL size reference
    const SIZES: [u64; 5] = [
        64 * 1000,
        256 * 1000,
        1 * 1000 * 1000,
        4 * 1000 * 1000,
        1 * 1000 * 1000 * 1000,
    ];
    // Tuple describing the file distribution
    const TIERS_SPEC: [[usize; 5]; 3] = [
        [1022, 256, 1364, 1364, 24],
        [164, 40, 220, 220, 4],
        [12, 4, 16, 16, 2],
    ];

    const TIERS: Range<u8> = 0..3;

    println!("running filesystem");
    println!("initialize state");
    let mut groups = vec![];
    let mut counter: u64 = 1;
    for t_id in 0..3 {
        groups.push(vec![]);
        let objs = groups.last_mut().unwrap();
        for (count, size) in TIERS_SPEC[t_id].iter().zip(SIZES.iter()) {
            for _ in 0..*count {
                let pref = pref(client.rng.gen_range(TIERS), Block::from_bytes(*size), &client);
                let key = format!("key{counter}").into_bytes();
                let (obj, _info) = client
                    .object_store
                    .open_or_create_object_with_pref(&key, pref)?;
                objs.push(key);
                counter += 1;
                let mut cursor = obj.cursor_with_pref(pref);
                with_random_bytes(&mut client.rng, *size, 8 * 1024 * 1024, |b| {
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
    const RUNS: usize = 10000;
    for run in 0..RUNS {
        println!("Reading generation {run} of {RUNS}");
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
