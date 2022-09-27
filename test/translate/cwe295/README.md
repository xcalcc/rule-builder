# Translating CWE295

Example rule taken from the CWE295 standard. 
Deals with the error caused by SSL not being verified first before connecting.

# Steps

```bash
../translate.py cwe295.mi -l java -r org.apache.commons-commons-email.o.vtable.mi --name CWE295" 
```

After executing, it should generate a CWE295.java where it contains the FSM rule file. You can inspect the file and find that it is made of transitions (FSM-related).
You can use CWE295.java for the next stage (compilation).
