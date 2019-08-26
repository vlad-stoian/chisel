# chisel - smaller tiles

## To install
```sh
cd ~/workspace
git clone git@github.com:vlad-stoian/chisel.git

cd chisel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## To run
```sh
python chisel.py --product-path ~/Downloads/pivotal-container-service-1.5.0-build.30.pivotal
```

## How does it work

#### Normal mode:

In BOSH, jobs can depend on packages (runtime dependencies), and packages can also depend on other packages (compile time dependencies).
Since bosh now provides compiled releases, the compile time packages are not needed anymore, even though BOSH still puts them inside the release.tgz.
What this does is scan for packages that no jobs depend on and calculates how much space you could save.


#### Insane mode:

In BOSH a normal release can have multiple jobs, but the tile doesn't necessarily use all of them. This means that theoretically those jobs and the packages they depend on could be removed. This looks at the tile manifest and tries to remove any job that's not defined either in the manifest or in the ODB manifest.

The problem with this is that the ODB service adapter might do some crazy things we're not aware, and removing all unused jobs might be risky.
