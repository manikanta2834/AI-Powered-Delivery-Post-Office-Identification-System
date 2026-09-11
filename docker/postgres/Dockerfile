FROM pgvector/pgvector:pg16 AS pgvector

FROM postgis/postgis:16-3.5

COPY --from=pgvector /usr/lib/postgresql/16/lib/vector.so /usr/lib/postgresql/16/lib/vector.so
COPY --from=pgvector /usr/share/postgresql/16/extension/vector--*.sql /usr/share/postgresql/16/extension/
COPY --from=pgvector /usr/share/postgresql/16/extension/vector.control /usr/share/postgresql/16/extension/vector.control
