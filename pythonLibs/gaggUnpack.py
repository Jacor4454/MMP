import os, shutil
from zipfile import ZipFile

# unpack the gagg ascii data into an "targetDir" folder

def unpack():
    main_folder = "assets/terr50_gagg_gb/data/"
    targetDir = "assets/raw_ascii"
    tempDir = "assets/temp"

    main_folder_d = os.fsencode(main_folder)

    for folder in os.listdir(main_folder_d):
        for file in os.listdir(main_folder + folder.decode("utf-8")):
            print(file)
            with ZipFile(main_folder + folder.decode("utf-8") + "/" + file) as zO:
                zO.extractall(path=tempDir)
            
            # go through all resulting files and remove all non .asc ones
            for unfile in os.listdir(tempDir):
                if unfile.endswith(".asc"):
                    # if ascii, move to output folder
                    try:
                        os.rename(os.path.join(tempDir, unfile), os.path.join(targetDir, unfile))
                    except:
                        print("please create folders raw_ascii in the assets folder")
                        exit()
                else:
                    # else delete file
                    if os.path.isfile(os.path.join(tempDir, unfile)) or os.path.islink(os.path.join(tempDir, unfile)):
                        os.unlink(os.path.join(tempDir, unfile))
                    elif os.path.isdir(os.path.join(tempDir, unfile)):
                        shutil.rmtree(os.path.join(tempDir, unfile))
