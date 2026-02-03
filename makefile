CC = gcc
CFLAGS = -Wall -O0 -ffreestanding
LDFLAGS = -T linker/linker.ld -Wl,-Map=build/output.map

SRC = src/main.c src/startup.c
OUT = build/output.elf

all: $(OUT)

$(OUT):
	mkdir -p build
	$(CC) $(CFLAGS) $(SRC) $(LDFLAGS) -o $(OUT)

clean:
	rm -rf build
