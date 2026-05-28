#ifndef MAIN_H
#define MAIN_H

#include "stm32f4xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"

#ifdef __cplusplus
extern "C" {
#endif

// Donanım Pin Tanımları
#define EMERGENCY_STOP_PIN       GPIO_PIN_13
#define EMERGENCY_STOP_PORT      GPIOC

#define MOTOR_LEFT_PIN           GPIO_PIN_6
#define MOTOR_LEFT_PORT          GPIOA
#define MOTOR_RIGHT_PIN          GPIO_PIN_7
#define MOTOR_RIGHT_PORT         GPIOA

// Yeni Donanım Pin Tanımları
#define LEAK_SENSOR_PIN          GPIO_PIN_4
#define LEAK_SENSOR_PORT         GPIOA

#define ULTRASONIC_TRIG_PIN      GPIO_PIN_5
#define ULTRASONIC_TRIG_PORT     GPIOA
#define ULTRASONIC_ECHO_PIN      GPIO_PIN_0
#define ULTRASONIC_ECHO_PORT     GPIOB

#define CURRENT_SENSOR_PIN       GPIO_PIN_0
#define CURRENT_SENSOR_PORT      GPIOA

// UART DMA Tampon Boyutu (main.c ve stm32f4xx_it.c arasında paylaşılır)
#define USART1_RX_BUF_SIZE 256

// Hata İşleme
void Error_Handler(void);

#ifdef __cplusplus
}
#endif

#endif // MAIN_H
