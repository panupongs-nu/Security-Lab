#!/bin/bash

# Ensure pv (Pipe Viewer) is installed for progress diplay
if ! command -v pv &> /dev/null
then 
	echo "The 'pv' utility is not installed. Installing it now..."
	sudo apt install -y pv
fi

# Declare file sizes with labels for Set1 (KB), Set2 (MB), and Set3 (GB)
sizes_set1=("1KB:1024" "2KB:2048" "4KB:4096" "8KB:8192"
	"16KB:16384" "32KB:32768" "64KB:65536" "128KB:131072"
	"256KB:262144" "512KB:524288")

sizes_set2=("1MB:1048576" "2MB:2097152" "4MB:4194304"
	"8MB:8388608" "16MB:16777216" "32MB:33554432" "64MB:67108864"
	"128MB:134217728" "256MB:268435456" "512MB:536870912")


sizes_set3=("1GB:1073741824" "2GB:2147483648" "3GB:3221225472"
	"4GB:4294967296" "5GB:5368709120" "6GB:6442450944" "7GB:7516192768"
	"8GB:8589934592" "9GB:9663676416" "10GB:10737418240")


# Function to create files based on the sizes
create_files(){
	local -n size_list=$1
	for size_label in "${size_list[@]}"
	do
		label=$(echo "$size_label" | cut -d':' -f1)
		size=$(echo "$size_label" | cut -d':' -f2)
		filename="file_${label}.txt"
		echo "Creating $filename with size $label ..."

		# Generate the file using random base64-encoded data
		base64 /dev/urandom | pv -s "$size" | head -c "$size" > "$filename"
		echo "$filename created."
	done
}

# Create files for Set1 (1KB to 512KB)
echo "Creating files for Set1 (1KB to 512KB)..."
create_files sizes_set1
# Create files for Set2 (1MB to 512MB)
echo "Creating files for Set2 (1MB to 512MB)..."
create_files sizes_set2
# Create files for Set3 (1GB to 10GB)
create_files sizes_set3

echo "All test files created successfully!"
