import hashlib
import itertools
import time
import multiprocessing as mp
from tqdm import tqdm
from datetime import datetime
import os

def hash_match(candidate, target_hashes, hash_algorithm):
    """Hash a candidate and check if it matches any target hashes."""
    if hash_algorithm == 'MD5':
        candidate_hash = hashlib.md5(candidate.encode('utf-8')).hexdigest()
    elif hash_algorithm == 'SHA-1':
        candidate_hash = hashlib.sha1(candidate.encode('utf-8')).hexdigest()
    elif hash_algorithm == 'SHA-256':
        candidate_hash = hashlib.sha256(candidate.encode('utf-8')).hexdigest()
    else:
        raise ValueError(f"Unsupported hash algorithm: {hash_algorithm}")
    
    return candidate_hash, candidate_hash in target_hashes

def worker(worker_id, charset, length, chunk_start, chunk_end, target_hashes, hash_algorithm, result_queue, progress_queue, start_time, log_file, progress_report_interval, stop_event):
    """Worker function that processes a chunk of the search space, checking for a stop signal."""
    total_combinations = chunk_end - chunk_start
    stop_check_interval = 10000

    candidate_space = itertools.product(charset, repeat=length)
    for _ in range(chunk_start):
        next(candidate_space)

    # Log the time the worker started processing
    with open(log_file, 'a') as log:
        start_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.write(f"Worker {worker_id} started processing at {start_timestamp}.\n")

    for index, candidate_tuple in enumerate(itertools.islice(candidate_space, chunk_end - chunk_start)):
        # Check the stop signal only after every stop_check_interval candidates
        if index % stop_check_interval == 0 and stop_event.is_set():
            with open(log_file, 'a') as log:
                log.write(f"Worker {worker_id} received stop signal and is stopping.\n")
            break

        candidate = ''.join(candidate_tuple)
        candidate_hash, is_match = hash_match(candidate, target_hashes, hash_algorithm)

        if is_match:
            elapsed_time = time.time() - start_time
            result_queue.put((candidate_hash, candidate, elapsed_time))
            progress_queue.put((worker_id, 1, total_combinations))

        if index % progress_report_interval == 0:
            progress_queue.put((worker_id, progress_report_interval, total_combinations))

    with open(log_file, 'a') as log:
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.write(f"Worker {worker_id} finished processing at {end_timestamp}.\n")

def main_process(num_workers, charset, length, target_hashes, hash_algorithm, chunk_size, output_file, log_file="worker_log.txt", hash_file=""):
    """Main process to coordinate workers and manage progress."""
    manager = mp.Manager()
    result_queue = manager.Queue()
    progress_queue = manager.Queue()

    total_combinations = len(charset) ** length
    # Set the maximum batch size to 2,000,000
    batch_size = min(max(int(total_combinations * 0.01), 100), 2000000)
    
    # Automatically adjust the progress report interval to be proportional to the batch size
    progress_report_interval = max(batch_size // 20, 10000)  # Use 5% of batch size, with a minimum of 10,000

    stop_event = mp.Event()

    chunks = [(i * chunk_size, min((i + 1) * chunk_size, total_combinations)) for i in range(num_workers)]

    start_time = time.time()
    with open(log_file, 'a') as log:
        main_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.write(f"Main process started at {main_start_time}\n")
        log.write(f"Hash values file: {hash_file}\n")
        log.write(f"Configuration: charset = {charset}, length = {length}, algorithm = {hash_algorithm}, batch size = {batch_size}, progress report interval = {progress_report_interval}\n")

    print(f"Using {num_workers} worker processes with batch size {batch_size}, charset {charset}, length {length}, and algorithm {hash_algorithm}")

    processes = []
    for worker_id, (start, end) in enumerate(chunks):
        p = mp.Process(target=worker, args=(worker_id, charset, length, start, end, target_hashes, hash_algorithm, result_queue, progress_queue, start_time, log_file, progress_report_interval, stop_event))
        processes.append(p)
        p.start()

        time.sleep(1)  # Staggered delay before starting the next worker

    overall_pbar = tqdm(total=total_combinations, desc="Overall Progress", unit="combination", mininterval=2, dynamic_ncols=True)
    found_pbar = tqdm(total=len(target_hashes), desc="Pre-images Found", unit="pre-image", mininterval=2, dynamic_ncols=True)

    results = []
    found_pre_images = 0

    while any(p.is_alive() for p in processes) or not result_queue.empty() or not progress_queue.empty():
        try:
            worker_id, progress, total = progress_queue.get(timeout=0.1)
            overall_pbar.update(progress)
        except:
            pass

        while not result_queue.empty():
            candidate_hash, candidate, elapsed_time = result_queue.get()
            found_pbar.update(1)
            results.append((candidate_hash, candidate, elapsed_time))
            found_pre_images += 1

            if found_pre_images >= len(target_hashes):
                stop_event.set()  # Signal all workers to stop
                break

    for p in processes:
        p.join()

    overall_pbar.close()
    found_pbar.close()

    total_elapsed_time = time.time() - start_time
    average_time_per_pre_image = total_elapsed_time / found_pre_images if found_pre_images > 0 else 0

    with open(log_file, 'a') as log:
        log.write(f"Search completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Total elapsed time: {total_elapsed_time:.2f} seconds\n")
        log.write(f"Average time per pre-image: {average_time_per_pre_image:.2f} seconds\n")
        log.write(f"--------------------------------------------\n")

    print(f"\nTotal Elapsed Time: {total_elapsed_time:.2f} seconds")

    with open(output_file, 'w') as f_out:
        f_out.write('Target Hash,Pre-image,Elapsed Time (s)\n')
        for candidate_hash, candidate, elapsed_time in results:
            f_out.write(f"{candidate_hash},{candidate},{elapsed_time:.2f}\n")

    return len(results), total_elapsed_time

def load_target_hashes_and_config(file_path):
    """Load the target hashes and configuration from the file, with error handling for file not found."""
    if not os.path.exists(file_path):
        print(f"Error: The file '{file_path}' was not found. Please check the file path and try again.")
        return None, None

    target_hashes = set()
    config = {"charset": 1, "algorithm": "MD5", "length": 4}  # Default config

    with open(file_path, 'r') as f:
        for line in f:
            if line.startswith("#charset:"):
                config["charset"] = int(line.split(":")[1].strip())
            elif line.startswith("#algorithm:"):
                config["algorithm"] = line.split(":")[1].strip()
            elif line.startswith("#length:"):
                config["length"] = int(line.split(":")[1].strip())
            elif not line.startswith("#"):  # Target hashes
                hash_val = line.strip().lower()
                if hash_val:
                    target_hashes.add(hash_val)
    return target_hashes, config

def charset_option(charset_id):
    """Map charset ID to actual charset string."""
    charset_options = {
        1: '0123456789',
        2: '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        3: '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
        4: '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()-_=+[]{}|;:",.<>?/~`'
    }
    return charset_options.get(charset_id, '0123456789')  # Default to numbers only

def main():
    print("Brute-force Hash Search Program")

    input_file = input("Enter the path to the file containing target hash values and configuration: ")
    target_hashes, config = load_target_hashes_and_config(input_file)

    if target_hashes is None or config is None:
        return  # Exit the program if the file is not found or is invalid

    charset = charset_option(config["charset"])
    hash_algorithm = config["algorithm"]
    length = config["length"]

    available_cores = mp.cpu_count()
    num_workers = int(input(f"Enter the number of worker processes to use (1-{available_cores}): "))
    log_file = "worker_log.txt"

    total_combinations = len(charset) ** length
    chunk_size = total_combinations // num_workers

    output_file = f"output_workers_{num_workers}_charset_{config['charset']}_algo_{hash_algorithm}_length_{length}.csv"

    found_pre_images, total_elapsed_time = main_process(num_workers, charset, length, target_hashes, hash_algorithm, chunk_size, output_file, log_file, input_file)

    print(f"Search complete! Total pre-images found: {found_pre_images}")
    print(f"Results written to: {output_file}")
    print(f"Worker logs can be found in: {log_file}")

if __name__ == "__main__":
    main()
