swig -python -c++ -o vbw_sc_wrap.cpp vbw_sc.i
g++ -c VBW_sc.cpp vbw_sc_wrap.cpp -shared -fpic -I/usr/include/python3.8 -fopenmp -O3 -lgsl -lgslcblas -lm -std=c++11
g++ -shared VBW_sc.o vbw_sc_wrap.o -o _vbwSC.so -fopenmp -lgsl -lgslcblas -lm -std=c++11
