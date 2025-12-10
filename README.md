# ms_pre

## Mass Spectrometry Preprocessing Tool

### About

ms_pre is a Python-based tool designed for preprocessing and handling mass spectrometry data.
It provides scripts and modules to streamline data management, transformation, and preparation for further analysis or pipeline integration.

### Features
* Easy setup using a virtual environment
* Cross-platform support (Windows, macOS, Linux)
* Configurable dependencies via requirements.txt
* Lightweight and modular structure

### Installation

1️. Clone the repository
```BASH
git clone https://github.com/EnriqueMA-jar/ms_pre.git
```

2️. Move into the main directory
```BASH
cd ms_pre
```

3️. Create a virtual environment
#### Windows (PowerShell o CMD)
```BASH
py -m venv <environment_name>
```
#### Linux / macOS
```BASH
python3 -m venv <environment_name>
```
### NOTE: Most of the dependencies works on Python 3.13, if you're using Python 3.14 you can use Conda to create the virtual enviroment
#### CONDA VIRTUAL ENVIROMENT
```BASH
conda create -n <enviroment_name> python=3.13
```

4️. Activate the virtual environment
#### Windows – PowerShell
```BASH
.\<environment_name>\Scripts\Activate.ps1
```
#### Windows – CMD
```BASH
<environment_name>\Scripts\activate.bat
```
#### Windows – Git Bash
```BASH
source <environment_name>/Scripts/activate
```
#### Linux / macOS
```BASH
source <environment_name>/bin/activate
```
#### CONDA
```BASH
conda activate <environment_name>
```
### Install dependencies
After activating the environment:
```BASH
pip install -r requirements.txt
```
### Run the main application
```BASH
py main.py
```
## Useful commands
### If you get the error:
```BASH
File cannot be loaded because running scripts is disabled on this system
```
### Enable script execution (on Windows PowerShell):
```BASH
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
### Deactivate the virtual environment:
```BASH
deactivate
```
## Requirements
* Python 3.10 or higher (up to 3.13)
* pip installed
* git instaled
* Internet connection for dependency installation

## PULLING NEW CHANGES FROM THE REPOSITORY:
```BASH
git stash
git pull
```
