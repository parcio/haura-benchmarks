FROM python

RUN pip3 install pandas matplotlib numpy

# This dockerfile solely exists because there does not seem to be a nice official matplolib+pandas+numpy container.
# 
