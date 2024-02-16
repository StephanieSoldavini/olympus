double fRand()
{
    double fMin = -1;
    double fMax = 1;
    double f = (double)rand() / RAND_MAX;
    return fMin + f * (fMax - fMin);
}

