FROM continuumio/miniconda3

ADD environment.yml /tmp/environment.yml
COPY . /usr/local/wfapp_py2


RUN apt-get update && apt-get install -y build-essential
RUN apt-get install -y libpq-dev python3-dev
RUN apt-get install -y libspatialindex-dev python-rtree
RUN apt-get install -y libopenjp2-7-dev

RUN conda env create -f /tmp/environment.yml

RUN echo "source activate $(head -1 /tmp/environment.yml | cut -d' ' -f2)" > ~/.bashrc
ENV PATH /opt/conda/envs/$(head -1 /tmp/environment.yml | cut -d' ' -f2)/bin:$PATH
SHELL ["conda", "run", "-n", "RIOS", "/bin/bash", "-c"]

WORKDIR /usr/local/wfapp_py2
RUN chmod +x api.py
RUN pip install -r requirements.txt

#RUN \
# apk add --no-cache postgresql-libs && \
# apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
# pip install -r requirements.txt --no-cache-dir && \
# apk --purge del .build-deps

#CMD [“python”, “api.py”]

EXPOSE 5050

CMD ["conda", "run", "-n", "RIOS", "python", "api.py"]
#ENTRYPOINT ["python", "api.py"]