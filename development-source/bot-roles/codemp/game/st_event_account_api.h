#ifndef ST_EVENT_ACCOUNT_API_H
#define ST_EVENT_ACCOUNT_API_H
#include "st_event.h"
typedef struct {
 int version; unsigned int size;
 int (*SetAccount)(int slot,const unsigned char generation[16],const STEProfile*);
 void (*ClearAccount)(int slot);
 int (*GetSnapshot)(STEvent* output,unsigned int size);
} STEventAccountAPI;
#endif
