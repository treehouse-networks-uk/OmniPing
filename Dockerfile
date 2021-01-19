FROM  ubuntu:20.04

MAINTAINER TreeHouseNetworks <gareth@treehousenetworks.co.uk>

# Install dependancies etc
RUN apt update && \
    apt install git curl iputils-ping traceroute python3.8 python3-pip  -y
# Get OmniPing and install depndencies
RUN git clone https://github.com/treehouse-networks-uk/OmniPing.git OmniPing
RUN cd OmniPing && \ 
    pip3 install -r requirements.txt

# Set working directory
WORKDIR /OmniPing
# Expose port
EXPOSE 8080/tcp
# Run OmniPing 
ENTRYPOINT python3 www_omniping.py
