# main.py

if __name__ == '__main__':
    import argparse
    import re
    import os
    from cryptography.fernet import Fernet

    parser = argparse.ArgumentParser(
        description='Encrypt or decrypt configuration file')
    parser.add_argument(
        '--mode', '-m', help='Specify what to do with input file', choices=['encrypt', 'decrypt'], required=True)

    parser.add_argument('--key', '-k',
                        help='Specify file containing secret key', metavar='key',  required=True)
                        
    parser.add_argument('--file', '-f', metavar='input_file', dest='input_file', type=argparse.FileType('rb+'),
                        help='Specify path to input file in ascii', required=True)

    try:
      args = parser.parse_args()   
    except Exception:
        exit(-1)

    if not os.path.isfile(args.key):
        open(args.key, 'x')
    
    try:
        args.key = open(args.key,'rb+')
    except Exception:
        exit(-1)
    
    args.input_file.close()

    # now open file the way we want
    if args.mode == 'encrypt':
        args.input_file = open(args.input_file.name, 'r+')

    if args.mode == 'decrypt':
        args.input_file = open(args.input_file.name, 'rb+')

    # if mode is encrypt - whole file is a single string, if decrypt - binary data
    data = args.input_file.read()

    match = False

    if args.mode == 'encrypt':
        match = (len(re.findall('\ABEGIN', data)) +
                 len(re.findall('END\Z', data))) == 2

    if args.mode == 'decrypt':
        if match:
            print('Decrypting decrypted file does not make any sense')
            exit(-1)

    if args.mode == 'encrypt':
        if not match:
            data = 'BEGIN\n' + data
            data += '\nEND'

    # DO STUFF WITH ENCRYPTION OR DECRYPTION
    out_data = str()

    args.input_file.close()

    if args.mode == 'encrypt':
        key = Fernet.generate_key()
        fernet = Fernet(key)
        out_data = fernet.encrypt(data.encode('ascii'))
        
        args.key.truncate(0)
        args.key.write(key)

        args.input_file = open(args.input_file.name, 'wb')

    if args.mode == 'decrypt':
        try:
            fernet = Fernet(args.key.read())
            out_data = fernet.decrypt(data)
        except Exception:
            print('Invalid input, file is decrypted')
            exit(-2)
        args.input_file = open(args.input_file.name, 'w')
        out_data = out_data.decode('ascii')
        
        if (len(re.findall('\ABEGIN', out_data)) +
                 len(re.findall('END\Z', out_data))) != 2:
            print('Decryption failed, corrupted file or key is wrong')
            exit(-1)
    

    # save and exit the program
    args.input_file.write(out_data)
    args.input_file.close()
    args.key.close()

    exit(0)
