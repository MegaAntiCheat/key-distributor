CREATE VIEW human_readable_pki AS
    SELECT sid_64+9223372036854780000, encode(pub_key_fingerprint::bytea, 'hex'), created FROM pki;

SELECT * FROM human_readable_pki;