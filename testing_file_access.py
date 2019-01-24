with open("dwf_location.txt", "r") as dwf_location:
    location = dwf_location.read().replace('\n', '')
    print(location)
