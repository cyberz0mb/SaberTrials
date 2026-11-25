// Some SP BSPs used in multiplayer contain unlit grid samples beyond the
// single-player route. Honour the mapper's explicit minimum in those cells.
#pragma once
#include <cmath>
#include <cstdio>

inline void ST_ParseGridMinimum(const char *value, float minimum[3]) {
    float rgb[3];
    int count=std::sscanf(value,"%f %f %f",&rgb[0],&rgb[1],&rgb[2]);
    if (count==1) rgb[1]=rgb[2]=rgb[0];
    else if (count!=3) return;
    for (int c=0;c<3;++c)
        if (!std::isfinite(rgb[c]) || rgb[c]<0 || rgb[c]>255) return;
    for (int c=0;c<3;++c) minimum[c]=rgb[c];
}

template<class Sample>
inline void ST_ApplyGridMinimum(Sample &sample, const float minimum[3]) {
    if (sample.styles[0]!=LS_NORMAL || sample.styles[1]!=LS_LSNONE) return;
    for (int c=0;c<3;++c)
        if (sample.ambientLight[0][c] || sample.directLight[0][c]) return;
    for (int c=0;c<3;++c) sample.ambientLight[0][c]=(byte)minimum[c];
}
