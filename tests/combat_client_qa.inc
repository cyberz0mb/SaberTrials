/* Inserted in an isolated QA build only. Never shipped. */
extern int bg_parryDebounce[NUM_FORCE_POWER_LEVELS];
static void CG_STPredictionQA_f(void) {
    trap->Print("QA prediction recovery=%i,%i,%i,%i\n", bg_parryDebounce[0],
        bg_parryDebounce[1], bg_parryDebounce[2], bg_parryDebounce[3]);
}
