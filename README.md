# Nexus 3 Exporter

A little script for downloading all assets inside a Nexus 3 repository, following the repository's asset format.
For example, fed with a Nexus 3 Maven repositories, this script yields a standard Maven repository structure containing all artifacts.

## Usage

You need Python 3 to run this script. You also need to install the requirements listed in `requirements.txt` (e.g., using pip).

Launch the script with:

    python3 nexus3_exporter.py [-h] [-o output_dir] [-u username] [-n] <server> <repo>

You have to supply two arguments:

* `server` is the root URL to the Nexus 3 server which contains the repository. For example, this might be `https://repo.loadingbyte.com`.
* `repo` is the name of the repository whose assets shall be downloaded. For example, this might be `maven-releases`.

Optionally, you can supply:

* `-h` shows a help page.
* `-o output_dir` specifies the directory where to store the downladed assets. If none is provided, the repository name will be used as the name of the output directory.
* `-u username` specifies an HTTP Basic Auth username. You will be prompted for the password.
* `-n` disables the SHA-1 hash verification of downloaded assets.

Example call:

    python3 nexus3_exporter.py https://repo.loadingbyte.com maven-releases

# Importing

This script only exports assets from Nexus 3 repositories, but not vice versa.
For importing assets, we recommend using the [official import scripts](https://github.com/sonatype-nexus-community/nexus-repository-import-scripts).