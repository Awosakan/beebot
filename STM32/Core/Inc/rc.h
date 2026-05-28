#ifndef RC_H
#define RC_H

#include <stdint.h>

#define RC_CHANNELS_COUNT 10

typedef struct {
    uint16_t channels[RC_CHANNELS_COUNT];
    uint8_t link_ok; // 1 = RC receiver connected and transmitting, 0 = connection lost
} RC_Data_t;

void rc_init(void);
void rc_parse_byte(uint8_t byte);
void rc_update(uint32_t current_time_ms);
RC_Data_t rc_get_data(void);

#endif // RC_H
