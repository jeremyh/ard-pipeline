

Run `./create-module.sh` to create an NCI module.

It will show you the variables it's using and ask for confirmation.

You can override any variables by setting them in bash before calling.

```
❯ ./create-module.sh
##########################
module_dir = /g/data/up71/modules
swfo_version= swfo-0.0.2
gost_version = gost-0.0.3
modtran_version = 6.0.1
DATACUBE_CONFIG_PATH = /g/data/v10/public/modules/dea/20221025/datacube.conf
##########################

Packaging "ard-pipeline 20230823-1426" to "/g/data/up71/modules/ard-pipeline/20230823-1426"

Continue? [y/N]
```

The script `./create-dev-module.sh` gives an example of calling it with a different module location.

After loading the your new module, run `./check-environment.sh` to check that things load.

