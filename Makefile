PRIVATE_KEY=	private_key.json
PUBLIC_KEY=	public_key.json

PAYLOAD_SCHEMA_YAML=	hcert_schema.yaml
PAYLOAD_SCHEMA_JSON=	hcert_schema.json

ISSUER=		XX
KID=		7Ma02Zk3w6Y

KEYS=		$(PRIVATE_KEY) $(PUBLIC_KEY)
SCHEMA=		$(PAYLOAD_SCHEMA_YAML) $(PAYLOAD_SCHEMA_JSON)

PAYLOAD=	hcert_example_typical.json

ISSUER=		issuer
KID=		test2021
TTL=		7776000 # 90 days

CLEANFILES=	$(PAYLOAD_SCHEMA_JSON) $(PAYLOAD_SCHEMA_YAML) \
		hcert_example_*.{bin,txt,png} \
		size_*.{bin,txt,png}


all: $(KEYS) $(SCHEMA)

verify: $(PAYLOAD_SCHEMA_YAML)
	python3 schemacheck.py --input hcert_example_minimal.json $(PAYLOAD_SCHEMA_YAML)
	python3 schemacheck.py --input hcert_example_typical.json $(PAYLOAD_SCHEMA_YAML)
	python3 schemacheck.py --input hcert_example_large.json   $(PAYLOAD_SCHEMA_YAML)

test: $(KEYS) verify
	sh test.sh

$(PRIVATE_KEY):
	jwkgen --kty EC --crv P-256 --kid $(KID) > $@

$(PUBLIC_KEY): $(PRIVATE_KEY)
	jq 'del(.d)' < $< >$@

$(PAYLOAD_SCHEMA_YAML):
	curl -o $@ https://raw.githubusercontent.com/ehn-digital-green-development/hcert-schema/main/eu_hcert_v1_schema.yaml

$(PAYLOAD_SCHEMA_JSON): $(PAYLOAD_SCHEMA_YAML)
	python3 schemacheck.py --json $< >$@

reformat:
	isort hcert *.py
	black hcert *.py

clean:
	rm -f $(PRIVATE_KEY) $(PUBLIC_KEY) $(CLEANFILES)
