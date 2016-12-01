# Setting up a development environment using conda


## Prerequisite

You must have `conda` installed on your system. If you need to install
`conda`, the easiest way is to download
[Anaconda from Continuum Analytics](https://www.continuum.io/downloads).
Select the Python 3.5 version that corresponds to your operating system
and follow the instructions on Continuum's site.

`git` must also be available on your system.


## Install the development environment

1. Clone the `foss-heartbeat` repository:

    ```bash
    git clone https://github.com/sarahsharp/foss-heartbeat.git
    ```

2. Change directory into `foss-heartbeat`:

    ```bash
    cd foss-heartbeat
    ```

3. Create a conda environment using the contents of `environment.yml` to
   specify the dependencies:

    ```bash
    conda env create -f environment.yml
    ```

4. Activate the conda environment named `dev-foss` that was created in Step 3:

    ```bash
    source activate dev-foss
    ```

5. Congrats. You have installed the development environment.


## Deactivate the conda development environment

When you are done with development, the conda environment can be exited using:

    ```bash
    source deactivate
    ```
