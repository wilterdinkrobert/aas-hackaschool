FROM thingsboard/tb-gateway:3.4.6

RUN apt-get -y update && \
    apt-get install -y wget vim adduser sudo procps net-tools supervisor openssh-server && \
    rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/* /tmp/* /var/tmp*

# Run tb_gateway via supervisord
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
RUN sed -i 's/python \/thingsboard_gateway\/tb_gateway.py/\/usr\/bin\/supervisord/g' ./start-gateway.sh

ENV AAS_REGISTRY "http://aas-registry:8080"
ENV SM_REGISTRY "http://sm-registry:8080"
ENV AAS_ID "https://example.com/spruik/PackML-MQTT-Simulator"
ENV THINGSBOARD_HOST "localhost"
ENV THINGSBOARD_PORT "1883"
ENV THINGSBOARD_ACCESS_TOKEN "1234"

RUN mkdir -p /app
COPY tb_gateway_controller /app/
RUN cd /app && pip install . && cd -
