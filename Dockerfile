FROM python@sha256:75a17dd6f00b277975715fc094c4a1570d512708de6bb4c5dc130814813ebfe4
# 可先将上面python版本镜像安装到本地docker打上python-local的tag:
# docker pull python@sha256:75a17dd6f00b277975715fc094c4a1570d512708de6bb4c5dc130814813ebfe4
# docker tag python@sha256:75a17dd6f00b277975715fc094c4a1570d512708de6bb4c5dc130814813ebfe4 python-local
#FROM python-local

WORKDIR /app

COPY requirements.txt .
#RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt \
    || pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt \
    || pip install --no-cache-dir -i https://pypi.org/simple -r requirements.txt

COPY . .

#COPY ./alembic ./alembic
#COPY alembic.ini .

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]