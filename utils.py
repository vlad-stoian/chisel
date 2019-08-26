import json
import math
import os
import tarfile
import zipfile
from pathlib import Path

import yaml


def print_json(obj):
    print(json.dumps(obj.__dict__, default=lambda o: o.__dict__, indent=4))


def parse_release(release_tar):
    release_manifest = {}

    jobs_in_tar = {}
    packages_in_tar = {}
    job_manifests = {}

    has_compiled_releases = False

    for release_file in release_tar:
        if release_file.name.endswith("release.MF"):
            release_manifest_file = release_tar.extractfile(release_file)
            release_manifest = yaml.load(release_manifest_file.read(), Loader=yaml.FullLoader)

        if "jobs" in release_file.name and "tgz" in release_file.name:
            job_name = Path(release_file.name).stem
            jobs_in_tar[job_name] = release_file.size

            job_tar_file = release_tar.extractfile(release_file)
            job_tar = tarfile.open(mode="r:gz", fileobj=job_tar_file)

            for job_file in job_tar:
                if job_file.name.endswith("job.MF"):
                    job_manifest_file = job_tar.extractfile(job_file)
                    job_manifests[job_name] = yaml.load(job_manifest_file.read(), Loader=yaml.FullLoader)

        if "compiled_packages" in release_file.name and "tgz" in release_file.name:
            package_name = Path(release_file.name).stem
            packages_in_tar[package_name] = release_file.size

            has_compiled_releases = True

    if not has_compiled_releases:
        return False, release_manifest, {}, {}, {}

    packages = {}
    for pn in packages_in_tar:
        packages[pn] = []

    for jn in job_manifests:
        if "packages" not in job_manifests[jn]:
            print("Job '{}' in release '{}' doesn't contain packages section".format(jn, release_tar.name))
            continue
        for pn in job_manifests[jn]["packages"]:
            if pn not in packages:
                print("Package '{}' referenced in job manifest '{}' not found in tar".format(pn, jn))
            packages[pn].append(jn)

    return True, release_manifest, packages, packages_in_tar, jobs_in_tar


def parse_used_jobs(metadata):
    jobs_used = {}

    for instance_group in metadata["job_types"]:
        for job in instance_group["templates"]:
            jobs_used[job["release"]] = jobs_used.get(job["release"], []) + [job["name"]]

        manifest = yaml.load(instance_group["manifest"], Loader=yaml.FullLoader)
        if "service_deployment" in manifest:
            for release in manifest["service_deployment"]["releases"]:
                # TODO: check if name and jobs are in the odb_releases
                jobs_used[release["name"]] = jobs_used.get(release["name"], []) + release["jobs"]
    return jobs_used


def parse_product(product_file_path):
    if not os.path.isfile(product_file_path):
        raise ValueError("{} is not a file".format(product_file_path))

    if not zipfile.is_zipfile(product_file_path):
        raise ValueError("{} is not a zip file".format(product_file_path))

    product_file_size = os.path.getsize(product_file_path)

    product_zip = zipfile.ZipFile(product_file_path)
    metadata_zipinfo = product_zip.getinfo("metadata/metadata.yml")
    metadata_file = product_zip.open(metadata_zipinfo)
    metadata = yaml.load(metadata_file, Loader=yaml.FullLoader)

    jobs_used = parse_used_jobs(metadata)

    releases = [
        pf for pf in product_zip.infolist() if pf.filename.startswith("releases")
    ]

    size_saved = 0
    insane_size_saved = 0

    for release in releases:
        release_tar_file = product_zip.open(release)
        release_tar = tarfile.open(mode="r:gz", fileobj=release_tar_file)

        print("---")
        print("Parsing release: {}".format(release_tar.name))

        has_compiled, release_manifest, package_deps, package_sizes, job_sizes = parse_release(release_tar)

        release_name = release_manifest["name"]
        print("Release name: {}".format(release_name))
        print("Has compiled packages: {}".format(has_compiled))
        import pprint
        print("Packages:")
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(package_deps)

        size_saved = size_saved + sum([package_sizes[pn] for pn in package_deps if not package_deps[pn]])

        insane_size_saved = insane_size_saved + sum([package_sizes[pn] for pn in package_deps if len(
            [job for job in package_deps[pn] if job in jobs_used[release_name]]) == 0])
        insane_size_saved = insane_size_saved + sum([job_sizes[jn] for jn in job_sizes if jn not in jobs_used[release_name]])

    print("Normal: Could save up to {}".format(convert_size(size_saved)))
    print("Insane: Could save up to {}".format(convert_size(insane_size_saved)))

    return size_saved, insane_size_saved


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])
