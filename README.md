# ACVCut

This tool prototype shrinks Android apps towards executed code. 
Based on the instruction coverage measured by [ACVTool](https://github.com/pilgun/acvtool).

[![Software license](https://img.shields.io/github/license/pilgun/acvcut)](https://github.com/pilgun/acvcut/blob/master/LICENSE)
[![Python version](https://img.shields.io/badge/-Python%202.7-yellow)](https://github.com/pilgun/acvcut/blob/master/LICENSE)
[![DOI](https://zenodo.org/badge/231208698.svg)](https://zenodo.org/badge/latestdoi/231208698)

## Setup
- to setup config.json please check the Installation section, step 2 at the [ACVTool readme](https://github.com/pilgun/acvtool)
- `java` and `adb` should be available from the terminal
- run emulator
- check Python dependecies if the script crashes 

## Workflow
- an APK is being instrumented by ACVTool
- installed
- instrumentation process started (code coverage measurement)
- the app is ready for tests
- instruction coverage generated
- ACVCut shrinks the app and creates the shrunk version (shrunk.apk)

## Usage
```sh
> python2 prepare_wd.py <apk_path> --wd <working_dir> --package <package_name>
> python2 acvcut.py <apk_path> --wd <working_dir> --package <package_name>
```

## Notes

ACVCut is a proof of work tool that worked with the TimeBomb sample and the Twitter Lite app on the API 25 Android Emulator. 
The tool is likely to have bugs and may require some tweaks when run on other apps. 
