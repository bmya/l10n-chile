/* todos los que están repetidos */
create or replace view sii_dte_incoming_dupes as (
    select * from (
      SELECT id, name, date_invoice, document_number, total_amount, flow_status, invoice_id,
      ROW_NUMBER() OVER(PARTITION BY document_number ORDER BY id asc) AS Row
      FROM sii_dte_incoming
    ) dups
    where
    dups.document_number in (
    select document_number from (select * from (
      SELECT document_number,
      ROW_NUMBER() OVER(PARTITION BY document_number ORDER BY id asc) AS Row
      FROM sii_dte_incoming
    ) dups
    where
    dups.Row > 1) dup
    )
order by document_number, row
)
