CC = gcc -g -rdynamic
#Using -Ofast instead of -O3 might result in faster code, but is supported only by newer GCC versions
CFLAGS = -lm -pthread -O3 -march=native -Wall -funroll-loops -Wno-unused-result

all: distance distance-nosense

distance : distance.c
	$(CC) distance.c -o distance $(CFLAGS)
distance-nosense : distance_nosense.c
	$(CC) distance_nosense.c -o distance-nosense $(CFLAGS)
	chmod +x *.sh

clean:
	rm -rf distance distance-nosense
