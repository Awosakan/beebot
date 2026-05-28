#include "main.h"
#include "rc.h"
#include <string.h>

static volatile RC_Data_t rc_data;
static uint8_t parse_buf[64];
static uint8_t parse_idx = 0;
static uint8_t payload_len = 0;
static uint32_t last_packet_time = 0;

// CRSF CRC8 Hesaplama (Polinom: 0xD5)
static uint8_t crsf_crc8(const uint8_t *ptr, uint8_t len) {
    uint8_t crc = 0;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= ptr[i];
        for (uint8_t j = 0; j < 8; j++) {
            if (crc & 0x80) {
                crc = (crc << 1) ^ 0xD5;
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}

void rc_init(void) {
    taskENTER_CRITICAL();
    rc_data.link_ok = 0;
    for (int i = 0; i < RC_CHANNELS_COUNT; i++) {
        rc_data.channels[i] = 1500; // Nötr/boşta sinyal (1.5ms)
    }
    taskEXIT_CRITICAL();
    parse_idx = 0;
    payload_len = 0;
    last_packet_time = 0;
}

void rc_parse_byte(uint8_t byte) {
    if (parse_idx == 0) {
        if (byte == 0xC8) { // CRSF Alıcı Paket Adresi (0xC8)
            parse_buf[0] = byte;
            parse_idx = 1;
        }
    } 
    else if (parse_idx == 1) {
        // Paket uzunluğu (Frame Type + Payload + CRC)
        if (byte >= 3 && byte <= 60) {
            parse_buf[1] = byte;
            payload_len = byte;
            parse_idx = 2;
        } else {
            parse_idx = 0; // Hatalı uzunluk, sıfırla
        }
    } 
    else {
        parse_buf[parse_idx++] = byte;
        
        // Tüm paket okunduğunda (Address (1) + Length (1) + Length bytes)
        if (parse_idx == (payload_len + 2)) {
            // CRSF CRC8 Doğrulama (Type + Payload)
            uint8_t calc_crc = crsf_crc8(&parse_buf[2], payload_len - 1);
            uint8_t rx_crc = parse_buf[payload_len + 1];
            
            if (calc_crc == rx_crc) {
                // Sadece RC Kanal verisi (Type = 0x15) olan paketleri işle
                if (parse_buf[2] == 0x15) {
                    last_packet_time = HAL_GetTick();
                    
                    uint8_t *p = &parse_buf[3];
                    uint16_t crsf_channels[RC_CHANNELS_COUNT];
                    
                    // 11-bitlik kanal verilerini çözümleme (CRSF formatı)
                    crsf_channels[0] = (p[0] | ((uint16_t)p[1] << 8)) & 0x07FF;
                    crsf_channels[1] = ((p[1] >> 3) | ((uint16_t)p[2] << 5)) & 0x07FF;
                    crsf_channels[2] = ((p[2] >> 6) | ((uint16_t)p[3] << 2) | ((uint16_t)p[4] << 10)) & 0x07FF;
                    crsf_channels[3] = ((p[4] >> 1) | ((uint16_t)p[5] << 7)) & 0x07FF;
                    crsf_channels[4] = ((p[5] >> 4) | ((uint16_t)p[6] << 4)) & 0x07FF;
                    crsf_channels[5] = ((p[6] >> 7) | ((uint16_t)p[7] << 1) | ((uint16_t)p[8] << 9)) & 0x07FF;
                    crsf_channels[6] = ((p[8] >> 2) | ((uint16_t)p[9] << 6)) & 0x07FF;
                    crsf_channels[7] = ((p[9] >> 5) | ((uint16_t)p[10] << 3)) & 0x07FF;
                    crsf_channels[8] = ((p[10] >> 6) | ((uint16_t)p[11] << 2) | ((uint16_t)p[12] << 10)) & 0x07FF;
                    crsf_channels[9] = ((p[12] >> 1) | ((uint16_t)p[13] << 7)) & 0x07FF;
                    
                    taskENTER_CRITICAL();
                    for (int i = 0; i < RC_CHANNELS_COUNT; i++) {
                        // CRSF (172 - 1811) aralığını PWM (1000 - 2000us) aralığına ölçekle
                        // Formül: PWM = (CRSF - 992) * 5/8 + 1500
                        int32_t val = (int32_t)crsf_channels[i];
                        int32_t pwm = ((val - 992) * 5) / 8 + 1500;
                        if (pwm < 1000) pwm = 1000;
                        if (pwm > 2000) pwm = 2000;
                        rc_data.channels[i] = (uint16_t)pwm;
                    }
                    rc_data.link_ok = 1;
                    taskEXIT_CRITICAL();
                }
            }
            
            parse_idx = 0; // Bir sonraki paket için sıfırla
        }
    }
}

void rc_update(uint32_t current_time_ms) {
    // 500 ms boyunca kumandadan veri gelmezse bağlantı koptu sayılır (Watchdog)
    if (rc_data.link_ok && (current_time_ms - last_packet_time > 500)) {
        taskENTER_CRITICAL();
        rc_data.link_ok = 0;
        for (int i = 0; i < RC_CHANNELS_COUNT; i++) {
            rc_data.channels[i] = 1500; // Güvenlik için tüm kanalları nötre çek
        }
        taskEXIT_CRITICAL();
    }
}

RC_Data_t rc_get_data(void) {
    RC_Data_t temp;
    taskENTER_CRITICAL();
    memcpy(&temp, (void*)&rc_data, sizeof(RC_Data_t));
    taskEXIT_CRITICAL();
    return temp;
}
