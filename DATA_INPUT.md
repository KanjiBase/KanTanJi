# Kanji Input

Input for kanji is defined in rows, where odd rows carry the key (~ what to do with the value) and even rows carry the value itself.
Each row must have `ID` key with numeric ID value of the entry.

Each row must also define **exactly one** one of the following keys:

 - kanji - the row is a kanji definition, the row must be defined exactly once per unique ID
 - tango - the row carries a vocabulary entry for a kanji, e.g. there must exist a row with the same ID that has 'kanji' definition


### Minimal Example:
```
ID   1   kanji   思   　　　　 imi    myslet (emotivní)
ID   1   tango   思＜おも＞う  imi    myslet, věřit (něčemu)
```

### Key definitions
Always, when some key is required, it can be present only once in the row. Optional keys can be present multiple times.
It is also not important what order the keys are defined in.

Dependening on the keys mentioned above, the row also can or must define other keys:
 - kanji
   - imi - **required**, the meaning of the kanji symbol
   - onyomi - the onyomi reading, optional, defined once per unique reading
   - kunyomi - the kunyomi reading, optional, defined once per unique reading
 - tango
   - imi - **required**, the meaning of the vocabulary entry
   - tsukaikata - an example usage sentence, optional

That's it! 

Though, you can also define arbitrary key-value pairs you wish, these will be included in 'other', 'notes' etc. sections.

### Furigana
Firugana is crucial part of learning kanji. Here, any value (except the 'kanji' value itself) and also custom keys support furigana in the following way:

 - furigana on single kanji character `外＜がい＞人＜じん＞`　will add furigana to each character separately, which creates the best furigana where it is obvious
what character has which reading
 - kanji that canont be separated to individual readings can be defined as `＜大人＞＜おとな＞` where the furigana will be added as a centered group above the 
whole vocabulary element - the word; note that there must not be a space anywhere between `><` characters

### Importance of Entries - Key Marks
Every single key supports importance marks, for example `kanji--`. This is also a 'kanji' key, but it has two level less importance status, because
there are two minus signs. It is up to the application (PDF / Anki ...) whether its generator interprets these importance levels in any way, or ignores them completely. For example, HTML sheets might respect `tango-` as less relevant vocabulary entry and show it to the users, but ignore `imi---` since there
is exactly one such kye required, and it does not make much sense to have 'less important meaning'. `ID` importance marks are ignored completely.

## Example Data and Output

```
1       2       3           4               5       6                           7                   8           9               10
ID     184     kanji       晴              imi     uklidnit, vyjasnit          onyomi              セイ         kunyomi         は
```

TODO: Screenshot


```
1       2       3           4               5       6                           7                   8
ID     184     tango       晴<ha>れる       imi     vyčasit se, vyjasnit       備<び>考<こう>       晴<は>れ je "slunečno" 
```
TODO: Screenshot

