///! This file implements a scientific workflow style writing first serial data
///! onto a storage layer and then reading this data from storage in a somewhat
///! random but repeating pattern.
use betree_perf::*;
use betree_storage_stack::StoragePreference;
use rand::RngCore;
use std::{error::Error, io::Write};

pub fn run(mut client: Client, runtime: u64) -> Result<(), Box<dyn Error>> {
    const OBJECT_SIZE: u64 = 10 * 1024 * 1024 * 1024;
    const FETCH_SIZE: u64 = 12 * 1024 * 1024;
    const N_POSITIONS: u64 = 256;
    println!("running scientific_evaluation");

    let start = std::time::Instant::now();
    let (obj, _info) = client
        .object_store
        .open_or_create_object_with_pref(b"important_research", StoragePreference::FAST)?;
    let mut cursor = obj.cursor_with_pref(StoragePreference::FAST);

    with_random_bytes(&mut client.rng, OBJECT_SIZE, 8 * 1024 * 1024, |b| {
        cursor.write_all(b)
    })?;
    println!("Initial write took {}s", start.elapsed().as_secs());
    client.sync().expect("Failed to sync database");
    // Generate positions to read
    let mut positions = vec![];
    for _ in 0..N_POSITIONS {
        let start = client.rng.next_u64() % (OBJECT_SIZE - 1);
        let length = client.rng.next_u64();
        positions.push((
            start,
            (length % FETCH_SIZE as u64)
                .clamp(0, OBJECT_SIZE.saturating_sub(start)),
        ));
    }

    let (obj, _info) = client
        .object_store
        .open_object_with_info(b"important_research")?
        .expect("Object was just created, but can't be opened!");

    let start = std::time::Instant::now();
    let mut buf = vec![0; FETCH_SIZE as usize];
    for (pos, len) in positions.iter().cycle() {
        // Read data as may be done in some evaluation where only parts of a
        // database file are read in.
        obj.read_at(&mut buf[..*len as usize], *pos).unwrap();
        if start.elapsed().as_secs() >= runtime {
            break;
        }
    }
    Ok(())
}
