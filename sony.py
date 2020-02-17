#https://bufferoverflows.net/exploring-pe-files-with-python/
import pefile

file = "d:\\Your files\\Sanin\\Downloads\\Update_ILCE7M3V310.exe"
pe = pefile.PE(file)
pe.print_info()  # Prints all Headers in a human readable format