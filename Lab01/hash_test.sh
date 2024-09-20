#!/bin/bash
# Declare file sizes with labels for set1 (KB), set2 (MB), and set3 (GB)
sizes_set1=("1KB" "2KB" "4KB" "8KB" "16KB" "32KB" "64KB" "128KB" "256KB" "512KB")
sizes_set2=("1MB" "2MB" "4MB" "8MB" "16MB" "32MB" "64MB" "128MB" "256MB" "512MB")
sizes_set3=("1GB" "2GB" "3GB" "4GB" "5GB" "6GB" "7GB" "8GB" "9GB" "10GB")

# Prompt user to select hash algorithm
echo "Select hash algorithm to test:1) MD5 2) SHA-1 3) SHA-256"
read -p "Enter the number (1, 2, or 3): " algo_choice

# Set algorithm and log file name based on user choice
case "$algo_choice" in
	1)algo_name="MD5" 	algo_cmd="md5sum" ;;
	2)algo_name="SHA-1"	algo_cmd="sha1sum";;
	3)algo_name="SHA-256"	algo_cmd="sha256sum";;
	*)echo "Invalid choice. Please choose 1, 2, or 3." exit 1 ;;
esac

# log file to store hash results
log_file="hash_results_${algo_name}.log"
# clear the log file if it exists
> "$log_file"

# Function to hash files three times and calculate average time
hash_files(){
  local -n size_list=$1
  for label in "${size_list[@]}"; do
      filename="file_${label}.txt"
      if [[ -f "$filename" ]]; then
         echo "Hashing $filename with $algo_name ..." | tee -a "$log_file"
	 total_time=0
	 for i in {1..3}; do
	    # Extract the real time (in seconds) for the hash computation
	    real_time=$({ time "$algo_cmd" "$filename" >/dev/null;} 2>&1 | grep real | awk '{print $2}')
	    minutes=$(echo "$real_time" | cut -d'm' -f1)
	    seconds=$(echo "$real_time" | cut -d'm' -f2 | sed 's/s//')
	    # Convert minutes to seconds and add to total
	    total_time=$(echo "$total_time + ($minutes * 60) + $seconds" | bc)
          done
	  # Calculate average time
	  avg_time=$(echo "scale=3; $total_time / 3" | bc)
	  echo "Average Time ($algo_name): $avg_time seconds" | tee -a "$log_file"
	  echo "" | tee -a "$log_file" # Add an empty line for readability
        else echo "File $filename not found. Skipping..." | tee -a "$log_file"
        fi
  done
}

# Hash files for set1 (1KB to 512KB)
echo "Hashing files for Set1 (1KB to 512KB) using $algo_name ..." | tee -a "$log_file"
hash_files sizes_set1
# Hash files for set2 (1MB to 512MB)
echo "Hashing files for Set2 (1MB to 512MB) using $algo_name ..." | tee -a "$log_file"
hash_files sizes_set2
# Hash files for set3 (1GB to 10GB)
echo "Hashing files for set3 (1GB to 10GB) using $algo_name..." | tee -a "$log_file"
hash_files sizes_set3

echo "Hashing completed. Results recorded in $log_file"

