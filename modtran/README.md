# Experiments with Modtran 6 licensing

## Download and extract the government license evalution copy
-   download from https://download.spectral.com/dnload04 with the vendor provided
    username and password
-   extract the tar file
      -   `tar xvf Mod6_0_2r3_g_full_allplat.tar`
-   extract the multipart 7zip file
      -   the `7za` provided with the tar does not quite work for us on AWS EC2
      -   `7za x Mod6_0_2r3_g_full_allplat.7z.001` works with the `7za` from the `p7zip` package on ubuntu
      -   I put the extracted files at `/home/ubuntu/projects/modtran6`

## Setup for the experiment
-   store the 24-digit product key in an environment variable
    (I put them in my `.bashrc`):

        export MODTRAN_PRODUCT_KEY='****-****-****-****-****-****-****'

## Run containerized `MODTRAN`
-   single instance:

        docker-compose build
        docker-compose up
        docker-compose down

    the output for the test-input-data.json should be under a folder in `./tests`

-   multiple instance:

        docker-compose build
        docker-compose up --scale=3
        docker-compose down

    there should be 3 different folders under `./tests`

## Notes
-   within the docker container we get an error message for the license activation:

        STAT_CRITICAL MODTRAN activation failed: unknown error.

    fortunately this does not stop modtran from running

-   when we run it from our EC2 instance this error message does not show up:

        STAT_VALID MODTRAN activation successful.
