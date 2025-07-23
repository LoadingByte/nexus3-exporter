#!/usr/bin/python3

import argparse
import hashlib
import os
from getpass import getpass
from json.decoder import JSONDecodeError
from urllib.parse import urljoin

import requests
import urllib3
from tqdm import tqdm


def main():
    # Disable unverified TLS certificate warnings.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    parser = argparse.ArgumentParser(
        description="A little script for downloading all assets inside a Nexus 3 repository, "
                    "following the repository's format (e.g., Maven 2).")
    parser.add_argument("server",
                        help="Root URL to Nexus 3 server; e.g., https://repo.loadingbyte.com")
    parser.add_argument("repo",
                        help="Name of repository whose assets shall be downloaded; e.g., maven-releases")
    parser.add_argument("-o", metavar="output_dir", dest="output_dir",
                        help="Directory where to store the downloaded assets; "
                             "if none is provided, the repository name will be used.")
    parser.add_argument("-u", metavar="username", dest="username",
                        help="HTTP Basic Auth username; you will be prompted for the password, "
                             "unless you supply it via the NEXUS_PASSWORD environment variable.")
    parser.add_argument("-n", dest="no_verify", action="store_true",
                        help="Disable the SHA-1 hash verification of downloaded assets.")
    parser.add_argument("-m", dest="mirror", action="store_true",
                        help="Mirror-mode; don't check whether the output directory is emtpy, "
                             "and skip downloading previously downloaded assets.")
    parser.add_argument("-q", dest="quiet", action="store_true",
                        help="Do not print anything but errors and two self-destroying progress bars.")

    args = parser.parse_args()
    server_url = args.server
    repo_name = args.repo
    output_dir = args.output_dir
    username = args.username
    no_verify = args.no_verify
    mirror = args.mirror
    quiet = args.quiet

    if not output_dir:
        output_dir = repo_name
    if os.path.exists(output_dir) and not mirror:
        if not quiet: print(f"Output directory '{output_dir}' already exists. Please delete it and then re-run the script.")
        abort(1)

    auth = (username, os.getenv("NEXUS_PASSWORD") or getpass()) if username else None

    if "://" not in server_url:
        server_url = "http://" + server_url

    if not quiet: print("Fetching asset listing...")
    asset_listing = fetch_asset_listing(quiet, auth, server_url, repo_name)
    if not quiet: print("Done!")

    if not quiet: print("Downloading and verifying assets...")
    download_assets(quiet, auth, output_dir, no_verify, asset_listing, mirror)
    if not quiet: print("Done!")


def abort(code):
    print("Aborting script!")
    exit(code)


def fetch_asset_listing(quiet, auth, server_url, repo_name):
    asset_api_url = urljoin(server_url, f"service/rest/v1/assets?repository={repo_name}")

    asset_listing = []
    continuation_token = -1  # -1 is a special value hinting the first iteration

    with tqdm(unit=" API requests", leave=not quiet) as pbar:
        while continuation_token:
            if continuation_token == -1:
                query_url = asset_api_url
            else:
                query_url = f"{asset_api_url}&continuationToken={continuation_token}"

            try:
                resp = requests.get(query_url, auth=auth, verify=False).json()
            except IOError as e:
                pbar.close()
                print(f"IO error: {e}")
                abort(2)
            except JSONDecodeError:
                pbar.close()
                print(f"Cannot decode JSON response. Are you sure that the server URL {server_url} is correct and "
                      f"the repository '{repo_name}' actually exists?")
                abort(3)

            continuation_token = resp["continuationToken"]
            asset_listing += resp["items"]

            pbar.update()

    return asset_listing


def download_assets(quiet, auth, output_dir, no_verify, asset_listing, mirror):
    with tqdm(asset_listing, leave=not quiet) as pbar:
        for asset in pbar:
            relative_path = asset["path"].lstrip("/")
            file_path = os.path.join(output_dir, relative_path)
            if mirror and os.path.isfile(file_path) and os.stat(file_path).st_size == asset["fileSize"]:
                continue
            error = download_single_asset(quiet, auth, file_path, no_verify, asset)

            if error:
                pbar.close()
                print(f"Failed downloading '{file_path}' due to the following error:")
                print(error)
                abort(4)


def download_single_asset(quiet, auth, file_path, no_verify, asset):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    for tryy in range(1, 11):
        try:
            r = requests.get(asset["downloadUrl"], auth=auth, verify=False)
            with open(file_path, "wb") as f:
                f.write(r.content)
        except IOError as e:
            # The requests API tries multiple times internally, so if it can't connect, the connection is probably down.
            return f"IO error: {e}"

        if no_verify:
            if not quiet: tqdm.write(f"Downloaded '{file_path}' (not verified!)")
            return False
        elif asset["checksum"]["sha1"] == sha1(file_path):
            if not quiet: tqdm.write(f"Downloaded and verified '{file_path}' (try {tryy})")
            return False
        else:
            tqdm.write(f"SHA-1 verification failed on '{file_path}' (try {tryy}); retrying...")

    # If, after 10 tries, the SHA-1 hash is still wrong, something's probably corrupted.
    return "Repeated SHA-1 verification failure"


def sha1(file_path):
    with open(file_path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


if __name__ == "__main__":
    main()
