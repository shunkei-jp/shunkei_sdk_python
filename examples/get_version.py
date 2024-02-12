from shunkei_sdk import ShunkeiVTX

def main():
    vtx = ShunkeiVTX.auto_connect()
    vtx.authorize(username="shunkei", password="shunkei")
    version = vtx.get_version()

    print("soft: " + version.software)
    print("hard: " + version.hardware)
    print("img: " + version.image)


if __name__ == "__main__":
    main()
