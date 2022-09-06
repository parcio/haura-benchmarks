///! This case implements a checkpoint like writing test in which multiple
///! objects are created on the preferred fastest speed and later migrated
///! downwards once they are no longer needed.
///!
///! A sync is performed after each object batch to ensure that data is safe
///! before continuing.
use betree_perf::*;
use betree_storage_stack::StoragePreference;
use rand::RngCore;
use std::{error::Error, io::Write};

pub fn run(mut client: Client) -> Result<(), Box<dyn Error>> {
    const N_OBJECTS: usize = 5;
    const OBJECT_SIZE_MIB: [u64; N_OBJECTS] = [256, 256, 1, 384, 128];
    const N_GENERATIONS: usize = 20;
    println!("running checkpoints");

    for gen in 0..N_GENERATIONS {
        for obj_id in 0..N_OBJECTS {
            let key = format!("{gen}_{obj_id}");
            let (obj, _info) = client
                .object_store
                .open_or_create_object_with_pref(key.as_bytes(), StoragePreference::FASTEST)?;
            // We definitely want to write on the fastest layer to minimize
            // waiting inbetween computation.
            let mut cursor = obj.cursor_with_pref(StoragePreference::FASTEST);
            with_random_bytes(&mut client.rng, OBJECT_SIZE_MIB[obj_id] * 1024 * 1024, 8 * 1024 * 1024, |b| {
                cursor.write_all(b)
            })?;
        }
        client.sync().expect("Failed to sync database");
    }
    client.sync().expect("Failed to sync database");
    Ok(())
}
