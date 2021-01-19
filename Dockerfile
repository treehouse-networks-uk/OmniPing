FROM  ubuntu:20.04

MAINTAINER TreeHouseNetworks <gareth@treehousenetworks.co.uk>

# Install dependancies etc
RUN apt update
RUN apt install traceroute net-tools python3.8 python3-pip curl git iputils-ping
RUN git clone https://github.com/treehouse-networks-uk/OmniPing.git
RUN pip3 install -r requirements.txt

# Expose port
EXPOSE 8080/tcp

# Run OmniPing 
ENTRYPOINT python3 www_omniping.py
