drop view line_tax_view;
create or replace view line_tax_view as (
	select
	invoice_id,
	journal_id,
	line_id,
	company_id,
	"TpoDoc",
	"NroDoc",
	"TpoImp",
	"TasaImp",
	"FchDoc",
	"RUTDoc",
	"RznSoc",
	"TpoDocRef",
	"FolioDocRef",
	(CASE
	WHEN tax_amount is not null THEN 0
	ELSE price_subtotal
	END) as "MntExe",
	(CASE
	WHEN tax_amount is null THEN 0
	ELSE price_subtotal
	END) as "MntNeto",
	round(
	(CASE WHEN tax_code = 15 then 0
	ELSE tax_amount END)
	 - (case when a.no_rec_code != '0' then
	tax_amount else 0 end) - 
	(case when iva_uso_comun then tax_amount 
	else 0 end), 2) as "MntIVA",
	(CASE
	WHEN a.tax_code != 14 then 1
	ELSE 0
	END) as "OtrosImp",
	(CASE
	WHEN a.tax_code != 14 then a.tax_code
	ELSE 0 END) as "CodImp",
	(CASE
	WHEN a.tax_code != 14 then "TasaImp"
	ELSE 0 END) as "aTasaImp",
	round((CASE
	WHEN a.tax_code = 15 THEN tax_amount
	ELSE 0
	END), 0) as "MntImp",
	round((CASE
	WHEN "TasaImp" = 19 AND a.tax_code = 15 
	THEN tax_amount ELSE 0 END), 2) 
	as "IVARetTotal",
	(CASE
	WHEN "TasaImp" < 19 AND a.tax_code = 15
	THEN tax_amount ELSE 0 END) 
	as "IVARetParcial",
	(case when a.no_rec_code != '0' then 1 else 0 end) as "IVANoRec",
	(case when a.no_rec_code != '0' then 
	cast(a.no_rec_code as integer) else 0 end) as "CodIVANoRec",
	cast(round((case when a.no_rec_code != '0' then
	tax_amount
	else 0 end), 0) as
	integer) as "MntIVANoRec",
	round((case when iva_uso_comun then
	tax_amount
	else 0 end), 2) as "IVAUsoComun",
	(case when a.no_rec then 0 else 0 end)
	as "MntSinCred",
	round(a.amount_total, 0) as "MntTotal",
	(case when a.no_rec then 0 else 0 end)
	as "IVANoRetenido"
	from
	(select 
	ai.id as invoice_id,
	aj.id as journal_id,
	ai.company_id,
	al.id as line_id,
	dcl.sii_code as "TpoDoc",
	cast(ai.sii_document_number as integer) as "NroDoc",
	(CASE WHEN at.sii_code in (14, 15) THEN 1 ELSE 0 END) as "TpoImp",
	round(abs(at.amount), 2) as "TasaImp",
	ai.date_invoice as "FchDoc",
	trim(leading '0' from substring(rp.vat from 3 for 8)) || '-' ||
	right(rp.vat, 1) as "RUTDoc",
	left(rp.name, 50) as "RznSoc",
	ref.sii_code as "TpoDocRef",
	ref.origen as "FolioDocRef",
	at.tax_group_id,
	at.no_rec,
	at.sii_code as tax_code,
	ai.iva_uso_comun,
	ai.no_rec_code,
	al.price_subtotal,
	abs(al.price_subtotal * at.amount / 100) as tax_amount,
	ai.amount_untaxed,
	ai.amount_total
	from account_invoice_line_tax alt
	join account_tax at
	on alt.tax_id = at.id
	right join account_invoice_line al
	on al.id = alt.invoice_line_id
	left join account_invoice ai
	on ai.id = al.invoice_id
	left join account_journal aj
	on aj.id = ai.journal_id
	left join sii_document_class dcl
	on dcl.id = ai.sii_document_class_id
	left join res_partner rp
	on rp.id = ai.partner_id
	left join 
	(select ar.invoice_id, ar.origen, dcl.sii_code from
	    (select
	    invoice_id,
	    origen,
	    "sii_referencia_TpoDocRef" as tipo
	    from account_invoice_referencias) ar
	left join sii_document_class dcl
	on ar.tipo = dcl.id) as ref
	on ref.invoice_id = ai.id
	/*where ai.id in (69, 70, 71, 78, 76, 77, 79)*/
	/* and aj.id in (id de los diarios de compra que se reportan) */
	order by ai.id, al.id, dcl.sii_code, at.id) a
)