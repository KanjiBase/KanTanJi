
# Kan<sup>Tan</sup>Ji &nbsp; 漢<sup>単</sup>字

> Simple KanJi training platform for czech audience.

Jednoduchá aplikace na trénování Kanji. Projekt vznikl jako spolupráce dobrovolníků
a japanistů na FF MUNI. Cílem je nabídnout různé způsoby učení kanji s kompletními
informacemi přímo v češtině.

[Vaše zpětná vazba je pro nás cenná! Prosíme, kontaktujte nás na stránce projektu.](https://github.com/KanjiBase/KanTanJi/issues)
Uvedený odkaz lze použít i pro pispívání do databáze.
Pokud chcete pomoci s přípravou obsahu a nebo máte jiný nápad, neváhejte nám dát vědět.

Kan<sup>Tan</sup>Ji je open-source projekt, a nemá žádný vztah s existujícími profily na sociálních sítích.

### FAQ
<details>
<summary>Jaký je stav projektu?</summary>
Kan<sup>Tan</sup>Ji může obsahovat drobné nedostatky, typicky způsobené lidskou chybou při zadávání tisíců slovíček
a příkladových vět - dejte nám vědět, pokud nějaké najdete! Japonský školní systém je hotový vždy po poslední sadu, 
ve které typicky chybí pár znaků, které se v BKB pořadí ještě nevyskytují. BKB pořadí je kompletní dle existující sady.
V budoucnu plánujeme pokračovat v množství podporovaných kanji.
</details>
<details>
<summary>
Řazení znaků a velikosti sad
</summary>
Řazení a velikosti nejsou zcela vymyšleny tak, aby vyhovovaly všem. Pořadí jsou k dispozici 
dle níže uvedených kapitol. Ke každému pořadí jsou dostupné všechny typy materiálů (PDF, Anki, HTML stránky, atp.).
V budoucnu bychom rádi rozšířili počet nánstrojů, které kanji umožňují studovat, a umožnili uživatelům vytvářet vlastní 
pořadí a vlastní velikosti sad.
</details>
<details>
<summary>Filtrování karet Anki</summary>
Karty KanTanJi mohou obsahovat více, než se chcete učit. Karty lze snadno filtrovat pomocí <strong>tagů</strong>. V současnosti jsou k dispozici tagy:
<ul>
 <li><strong>KanTanJi_Kanji</strong> (karta s kanji)</li>
 <li><strong>KanTanJi_Tango</strong> (slovní zásoba související s kanji)</li>
 <li><strong>KanTanJi_Learn_Now</strong> (slovní zásoba obsahující pouze kanji, která již byla naučena)</li>
 <li><strong>KanTanJi_Learn_Deck</strong> (slovní zásoba obsahující kanji, která se bude učit v aktuálním balíčku)</li>
 <li><strong>KanTanJi_Learn_Future</strong> (slovní zásoba obsahující kanji, která ještě nebyla naučena)</li>
</ul>
Pokud chcete například odstranit všechny karty s kanji a příliš obtížnou slovní zásobu obsahující kanji, 
která ještě nebyla naučena podle pořadí KanTanJi, můžete <strong>pozastavit</strong> karty s tagy 
'KanTanJi_Kanji' a 'KanTanJi_Learn_Future'.

Nejprve v aplikaci Anki <strong>otevřete Prohlížení karet (Browse Cards)</strong>. Poté v možnostech vyberte <strong>filtrovat podle tagu</strong>.
Když jsou zobrazeny pouze požadované karty, opět v možnostech zvolte <strong>vybrat všechny karty</strong> 
a nakonec také v možnostech vyberte <strong>pozastavit (suspend)</strong>.

Doporučujeme slučovat studované sady do jedné velké sady, aby bylo možné využít výhod chytrého opakování v Anki.
</details>
