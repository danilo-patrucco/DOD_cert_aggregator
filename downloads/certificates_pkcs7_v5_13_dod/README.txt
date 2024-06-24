############################################################################################################

certificates_pkcs7_v5_13_dod

############################################################################################################

File Information:

The structure of the file names for files that contain certificates in this bundle follow this pattern:

certificates_pkcs7_[bundle version]_[group]_[subgroup information].[encoding].[file type]

where:
    'bundle version' is a PKE version identification number of the form Major_Minor_Release.
    'group' is a DoD PKI certificate grouping which is either DoD, ECA, JITC, SIPR, DIL, or WCF.
    'subgroup information' is additional details about which Root CA the file contains (with the Root's subordinates).
    'encoding' is the encoding scheme used in the file and is either der or pem.
    'file type' is the file extension which best fits the contents of the file.

There is a special file which support the verification of this bundle. The file contains a CMS object which contains a
payload of file checksums included in this bundle and has been digitally signed by the DoD PKE code signing credential.
The structure of its file name follows this pattern:

certificates_pkcs7_[bundle version]_[group].sha256

where:
    'bundle version' is a PKE version identification number of the form Major_Minor_Release.
    'group' is a DoD PKI certificate grouping which is either DoD, ECA, JITC, SIPR, DIL, or WCF.

Verification:


To verify this PKCS#7 package please perform the following steps:


1)  Determine the Thumbprint on DoD Root CA 3 (the first dod_pke_chain.pem certificate) using the following command:
openssl x509 -in dod_pke_chain.pem -subject -issuer -fingerprint -noout

Verify the following output:
subject= /C=US/O=U.S. Government/OU=DoD/OU=PKI/CN=DoD Root CA 3
issuer= /C=US/O=U.S. Government/OU=DoD/OU=PKI/CN=DoD Root CA 3
SHA1 Fingerprint=D7:3C:A9:11:02:A2:20:4A:36:45:9E:D3:22:13:B4:67:D7:CE:97:FB


2) Verify the DoD Root CA 3 SHA1 Fingerprint against the value posted at https://crl.disa.mil:

- Select DOD ROOT CA 3 from the list of CAs (listed alphabetically) and click "Submit Selection"
- Click "View" to view the certificate
- Scroll to the bottom of the certificate page and verify that the listed SHA-1 Certificate Fingerprint matches the value output in step 1 above.


3) Verify that only DoD Root 3 is present in the dod_pke_chain.pem file using the following command:
openssl crl2pkcs7 -nocrl -certfile dod_pke_chain.pem | openssl pkcs7 -print_certs -noout

Verify the following output (subject/issuer for certificate should be CN=DoD Root CA 3):

subject=/C=US/O=U.S. Government/OU=DoD/OU=PKI/CN=DoD Root CA 3
issuer=/C=US/O=U.S. Government/OU=DoD/OU=PKI/CN=DoD Root CA 3

Confirm that only one certificate is listed - DoD Root CA 3.


4) Verify the S/MIME signature on certificates_pkcs7_v5_13_dod.sha256 using the following command:

On Mac OSX:
$ openssl smime -verify -in certificates_pkcs7_v5_13_dod.sha256 -inform DER -CAfile dod_pke_chain.pem | shasum -a 256 -c

Verify the following output:
Verification successful


On Linux:
$ openssl smime -verify -in certificates_pkcs7_v5_13_dod.sha256 -inform DER -CAfile dod_pke_chain.pem | dos2unix | sha256sum -c

Verify the following output:
Verification successful


On Windows:

Verify the signature on the hash file:
> openssl smime -verify -in certificates_pkcs7_v5_13_dod.sha256 -inform DER -CAfile dod_pke_chain.pem

Verify the following output:
Verification successful

Then for each file listed in the output of the openssl smime -verify command, generate a local hash:
> certutil -hashfile FILENAME sha256

Verify that the output matches the hash listed for the file in the certificates_pkcs7_v5_13_dod.sha256 openssl smime -verify output.


############################################################################################################

Usage:

Openssl - To export CA certificates to a concatenated PEM file for use as an openssl CAfile (named e.g. dod_CAs.pem), use the following command:
openssl pkcs7 -in certificates_pkcs7_v5_13_dod_der.p7b -inform der -print_certs -out dod_CAs.pem

For more detailed instructions find our Getting Started with Firefox on Linux guide on our DoD Cyber Exchange PKI-PKE site. End Users > Web Browsers > Mozilla Firefox