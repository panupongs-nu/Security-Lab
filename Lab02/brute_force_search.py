import hashlib
import itertools
import time
import multiprocessing as mp
import os
from tqdm import tqdm
import random

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

def worker(worker_id, charset, length, chunk_start, chunk_end, target_hashes, hash_algorithm, result_queue, progress_queue, base_batch_size, start_time):
    """Worker function that processes a chunk of the search space with staggered progress reporting."""
    total_combinations = chunk_end - chunk_start
    progress = 0

    # Create a staggered batch size for this worker based on worker_id to avoid reporting at the same time
    stagger_factor = random.uniform(0.8, 1.2)  # Random factor to stagger reporting
    batch_size = int(base_batch_size * stagger_factor)

    # Precompute the range of candidates for this worker
    for index in range(chunk_start, chunk_end):
        # Generate candidate using modular arithmetic to avoid the overhead of itertools.islice
        candidate = ''.join(charset[(index // len(charset) ** i) % len(charset)] for i in range(length))
        
        # Check if the candidate's hash matches any target
        candidate_hash, is_match = hash_match(candidate, target_hashes, hash_algorithm)
        if is_match:
            elapsed_time = time.time() - start_time  # Calculate elapsed time for the found pre-image
            result_queue.put((candidate_hash, candidate, elapsed_time))
            progress_queue.put((worker_id, 1, total_combinations))  # Update progress immediately after finding pre-image

        # Update progress after every staggered batch size
        progress += 1
        if progress % batch_size == 0:
            progress_queue.put((worker_id, batch_size, total_combinations))  # Correct batch size added

def main_process(num_workers, charset, length, target_hashes, hash_algorithm, base_batch_size, chunk_size, output_file):
    """Main process to coordinate workers and manage progress."""
    manager = mp.Manager()
    result_queue = manager.Queue()
    progress_queue = manager.Queue()

    # Determine the total number of combinations
    total_combinations = len(charset) ** length

    # Divide the total search space into chunks for each worker
    chunks = []
    for i in range(num_workers):
        start_index = i * chunk_size
        end_index = min(start_index + chunk_size, total_combinations)
        chunks.append((start_index, end_index))

    # Start worker processes
    start_time = time.time()
    processes = []
    for worker_id, (start, end) in enumerate(chunks):
        p = mp.Process(target=worker, args=(worker_id, charset, length, start, end, target_hashes, hash_algorithm, result_queue, progress_queue, base_batch_size, start_time))
        processes.append(p)
        p.start()

    # Monitor progress from workers
    overall_progress = 0
    overall_pbar = tqdm(total=total_combinations, desc="Overall Progress", unit="combination", mininterval=1, position=0, dynamic_ncols=True)
    found_pre_images = 0
    found_pbar = tqdm(total=len(target_hashes), desc="Pre-images Found", unit="pre-image", mininterval=1, position=1, dynamic_ncols=True)

    # Store the found results to write to the output file
    results = []

    while any(p.is_alive() for p in processes) or not result_queue.empty():
        try:
            # Update overall progress based on batch sizes correctly
            worker_id, progress, total = progress_queue.get(timeout=1)
            overall_pbar.update(progress)
        except:
            pass

        # Check the result queue for any found pre-images
        while not result_queue.empty():
            matches = result_queue.get()
            if matches:
                found_pre_images += 1
                found_pbar.update(1)  # Update the pre-image found progress immediately
                candidate_hash, candidate, elapsed_time = matches
                results.append((candidate_hash, candidate, elapsed_time))

    # Wait for all workers to finish
    for p in processes:
        p.join()
    
    overall_pbar.close()
    found_pbar.close()

    # Calculate and print the total elapsed time
    total_elapsed_time = time.time() - start_time
    print(f"\nTotal Elapsed Time: {total_elapsed_time:.2f} seconds")

    # Write the results to the output file
    with open(output_file, 'w') as f_out:
        f_out.write('Target Hash,Pre-image,Elapsed Time (s)\n')
        for candidate_hash, candidate, elapsed_time in results:
            f_out.write(f"{candidate_hash},{candidate},{elapsed_time:.2f}\n")

    return len(results), total_elapsed_time

def get_charset_option():
    """Helper function to get the charset based on user input."""
    print("Select the character set to use for generating pre-images:")
    print("1. Numbers only (0-9)")
    print("2. Numbers with capital letters (0-9, A-Z)")
    print("3. Numbers with case-sensitive letters (0-9, a-z, A-Z)")
    print("4. Alphanumeric with symbols")
    while True:
        choice = input("Enter your choice (1-4): ")
        if choice == '1':
            return '0123456789'
        elif choice == '2':
            return '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        elif choice == '3':
            return '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        elif choice == '4':
            return '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()-_=+[]{}|;:",.<>?/~`'
        else:
            print("Invalid choice. Please enter a number between 1 and 4.")

def load_target_hashes(file_path):
    """Load the target hashes from a file."""
    if not os.path.exists(file_path):
        print(f"Error: The file {file_path} does not exist.")
        return set()

    target_hashes = set()
    with open(file_path, 'r') as f:
        for line in f:
            hash_val = line.strip().lower()
            if hash_val:
                target_hashes.add(hash_val)
    return target_hashes

def main():
    print("Brute-force Hash Search Program")

    # Get the number of available CPU cores
    available_cores = mp.cpu_count()
    print(f"Number of available CPU cores: {available_cores}")

    # Get user inputs for parameters
    num_workers = int(input(f"Enter the number of worker processes to use (1-{available_cores}): "))
    length = int(input("Enter the length of the pre-image to search for: "))
    charset = get_charset_option()
    
    print("Select the hash algorithm:")
    print("1. MD5")
    print("2. SHA-1")
    print("3. SHA-256")
    while True:
        algo_choice = input("Enter the hash algorithm (1-3): ")
        if algo_choice == '1':
            hash_algorithm = 'MD5'
            break
        elif algo_choice == '2':
            hash_algorithm = 'SHA-1'
            break
        elif algo_choice == '3':
            hash_algorithm = 'SHA-256'
            break
        else:
            print("Invalid choice, please enter 1, 2, or 3.")

    # Load target hashes from the user-provided file
    while True:
        input_file = input("Enter the path to the file containing target hash values: ")
        target_hashes = load_target_hashes(input_file)
        if target_hashes:
            break

    # Ask for output file to save results
    output_file = input("Enter the path to the output file to write results (e.g., output.csv): ")
    if not output_file:
        output_file = 'output.csv'

    # Total combinations
    total_combinations = len(charset) ** length

    # Set base batch size and chunk size (for dividing tasks)
    base_batch_size = int(input("Enter the base batch size for progress updates (e.g., 1000): "))
    chunk_size = total_combinations // num_workers

    # Start the brute-force search
    found_pre_images, total_elapsed_time = main_process(num_workers, charset, length, target_hashes, hash_algorithm, base_batch_size, chunk_size, output_file)

    print(f"Search complete! Total pre-images found: {found_pre_images}")
    print(f"Results written to: {output_file}")

if __name__ == "__main__":
    main()
