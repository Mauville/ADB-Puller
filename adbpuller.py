from multiprocessing import Process, Pool
import os
import sys
import subprocess
from tqdm import tqdm

debug = False
processed_file = open("./processed.txt", "r+", encoding="utf-8")
current_object = ""
errors_file = open("./errors.txt", "w", encoding="utf-8")


class Directory:
    def __init__(self, path, files, subdirs):
        self.path = path
        self.files = files
        self.subdirs = subdirs


def debugPrint(s):
    if debug:
        print(s)


def loadCache():
    lines_set = set()
    try:
        for line in processed_file.readlines():
            lines_set.add(line.strip())
            debugPrint(f"CACHE:added {line}")
        print("Cache successfully loaded")
    except FileNotFoundError:
        print("No cache found")

    return lines_set


def mkParentDir(directory):
    parent_Name = directory.strip().split("/")[
        -3
    ]  # Extract parent name from the full path
    try:
        os.mkdir(f"./{parent_Name}")
    except FileExistsError:
        pass


def adb_devices_command():
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )
        if result.stdout.count("\n") <= 2:
            raise ConnectionError
    except subprocess.CalledProcessError as e:
        print(f"Error executing adb shell command '{command}': {e}")


def adb_shell_command(command):
    try:
        result = subprocess.run(
            ["adb", "shell", command],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )
        breakpoint
        if not result.stdout:
            return []
        return result.stdout.strip().split("\n")
    except subprocess.CalledProcessError as e:
        print(f"Error executing adb shell command '{command}': {e}")
        return []


def adb_pull(directory):
    global current_object
    current_object = directory
    try:
        # Run adb pull for the directory
        directory_Name = directory.strip().split("/")[
            -2
        ]  # Extract directory name from the full path
        parent_Name = directory.strip().split("/")[
            -3
        ]  # Extract parent name from the full path
        result = subprocess.run(
            ["adb", "pull", "-a", directory, "./" + parent_Name + "/" + directory_Name],
            check=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as e:
        print(f"Error pulling object '{directory}': {e}")
        errors_file.write(f"{current_object}\n")


def buildDirObject(directory_name):
    files = adb_shell_command(f"find {directory_name} -type f")
    directories = adb_shell_command(f"ls -d {directory_name}/*/")
    return Directory(directory_name, files, directories)


def traverseDir(path: str):
    # Get list of directories on the device
    directory = buildDirObject(path)
    if not directory.subdirs:
        if len(directory.files) > 1000:
            # Here we do the segmented pull to avoid errors
            segmented_adb_pull(directory.files)
        else:
            # Normal pull
            adb_pull(directory.path)
    else:
        # Traverse subdirs
        with Pool(len(directory.subdirs)) as p:
            p.map(traverseDir, directory.subdirs)


def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <device_directory>")
        print("Ideally, device_directory should be in /storage/emulated/0/")
        return

    device_directory = sys.argv[1]
    print(f"Pulling recursively from {device_directory}")

    # Check if connected
    adb_devices_command()

    # Multiprocessed code here for recursively pulling dirs using traverseDir
    p = Process(target=traverseDir, args=(device_directory,))
    p.start()
    p.join()

    # TODO cache doesnt work
    # make a good mkdir function that will make the dirs if they dont exist
    # write segmented pull function

    # print("Found these directories:")
    # print("\n".join([f"\t'{d}'" for d in directories]))

    # mkParentDir(device_directory)

    # # Implement caching
    # cache = loadCache()

    # if not directories:
    #     print(f"No directories found at '{device_directory}' on the device.\nTrying files")

    # for directory in tqdm(directories):
    #     if directory in cache:
    #         debugPrint(f"Found {directory} in cache file. Skipping...")
    #         continue
    #     print(f"Processing {directory}")
    #     adb_pull(directory)
    #     processed_file.write(directory + "\n")

    # print("\n\nPulling files now")
    # for file in tqdm(files):
    #     if file in cache:
    #         debugPrint(f"Found {file} in cache file. Skipping...")
    #         continue
    #     adb_pull(file)
    #     processed_file.write(file + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"Interrupted at object {current_object}.")
        print("Saving progress...")
    except ConnectionError:
        print(f"Device disconnected.")
    finally:
        errors_file.write(f"{current_object}\n")
        processed_file.close()
        errors_file.close()
