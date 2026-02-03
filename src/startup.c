#include <stdint.h>

/* Symbols from linker */
extern uint32_t _etext;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;

extern int main(void);

/* Reset handler */
void Reset_Handler(void)
{
    uint32_t *src = &_etext;
    uint32_t *dst = &_sdata;

    /* Copy .data from ROM to RAM */
    while (dst < &_edata)
    {
        *dst++ = *src++;
    }

    /* Zero initialize .bss */
    dst = &_sbss;
    while (dst < &_ebss)
    {
        *dst++ = 0;
    }

    main();

    while (1);
}
