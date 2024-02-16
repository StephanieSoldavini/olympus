#include "helmholtz.h"

void helmholtz(double S[121], double D[1331], double u[1331], double v[1331])
{
    double t[1331]; 
    double r[1331];
    double t1[1331]; 
    double t3[1331]; 
    double t0[1331]; 
    double t2[1331];
    double S_[121];
    for (int c = 0; c < 121; c += 1) {
    	S_[c] = S[c];
    }
    for (int c1 = 0; c1 <= 10; c1 += 1)
        for (int c2 = 0; c2 <= 10; c2 += 1)
            for (int c3 = 0; c3 <= 10; c3 += 1) {
                // stmt0
                t1[121 * c1 + 11 * c2 + c3] = 0;
                for (int c8 = 0; c8 <= 10; c8 += 1)
                    // stmt0
                    t1[121 * c1 + 11 * c2 + c3] = t1[121 * c1 + 11 * c2 + c3] + S_[11 * c1 + c8] * u[121 * c2 + 11 * c3 + c8];
            }
    for (int c1 = 0; c1 <= 10; c1 += 1)
        for (int c2 = 0; c2 <= 10; c2 += 1)
            for (int c3 = 0; c3 <= 10; c3 += 1) {
                // stmt1
                t0[121 * c1 + 11 * c2 + c3] = 0;
                for (int c8 = 0; c8 <= 10; c8 += 1)
                    // stmt1
                    t0[121 * c1 + 11 * c2 + c3] = t0[121 * c1 + 11 * c2 + c3] + S_[11 * c1 + c8] * t1[121 * c2 + 11 * c3 + c8];
            }
    for (int c1 = 0; c1 <= 10; c1 += 1)
        for (int c2 = 0; c2 <= 10; c2 += 1)
            for (int c3 = 0; c3 <= 10; c3 += 1) {
                // stmt2
                t[121 * c1 + 11 * c2 + c3] = 0;
                for (int c8 = 0; c8 <= 10; c8 += 1)
                    // stmt2
                    t[121 * c1 + 11 * c2 + c3] = t[121 * c1 + 11 * c2 + c3] + S_[11 * c1 + c8] * t0[121 * c2 + 11 * c3 + c8];
            }
    for (int c1 = 0; c1 <= 10; c1 += 1)
        for (int c2 = 0; c2 <= 10; c2 += 1)
            for (int c3 = 0; c3 <= 10; c3 += 1)
                // stmt3
                r[121 * c1 + 11 * c2 + c3] = D[121 * c1 + 11 * c2 + c3] * t[121 * c1 + 11 * c2 + c3];
    for (int c1 = 0; c1 <= 10; c1 += 1)
        for (int c2 = 0; c2 <= 10; c2 += 1)
            for (int c3 = 0; c3 <= 10; c3 += 1) {
                // stmt4
                t3[121 * c1 + 11 * c2 + c3] = 0;
                for (int c8 = 0; c8 <= 10; c8 += 1)
                    // stmt4
                    t3[121 * c1 + 11 * c2 + c3] = t3[121 * c1 + 11 * c2 + c3] + S_[c1 + 11 * c8] * r[121 * c2 + 11 * c3 + c8];
            }
    for (int c1 = 0; c1 <= 10; c1 += 1)
        for (int c2 = 0; c2 <= 10; c2 += 1)
            for (int c3 = 0; c3 <= 10; c3 += 1) {
                // stmt5
                t2[121 * c1 + 11 * c2 + c3] = 0;
                for (int c8 = 0; c8 <= 10; c8 += 1)
                    // stmt5
                    t2[121 * c1 + 11 * c2 + c3] = t2[121 * c1 + 11 * c2 + c3] + S_[c1 + 11 * c8] * t3[121 * c2 + 11 * c3 + c8];
            }
    for (int c1 = 0; c1 <= 10; c1 += 1)
        for (int c2 = 0; c2 <= 10; c2 += 1)
            for (int c3 = 0; c3 <= 10; c3 += 1) {
                // stmt6
                v[121 * c1 + 11 * c2 + c3] = 0;
                for (int c8 = 0; c8 <= 10; c8 += 1)
                    // stmt6
                    v[121 * c1 + 11 * c2 + c3] = v[121 * c1 + 11 * c2 + c3] + S_[c1 + 11 * c8] * t2[121 * c2 + 11 * c3 + c8];
            }
}

