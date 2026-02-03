#include <stdint.h>

/* Initialized global variable → .data */
int global_init = 10;

/* Uninitialized global → .bss */
int global_uninit;

/* Constant → .rodata */
const int global_const = 100;

int main(void)
{
    global_uninit = global_init + global_const;

    while (1)
    {
        /* Infinite loop like real embedded systems */
    }
}
