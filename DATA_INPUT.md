# Kanji Input

Input for kanji is defined in rows, where odd rows carry the key (~ what to do with the value) and even rows carry the value itself.
Each row must have `ID` key with numeric ID value of the entry (it can also be versioned by dots if you want to use hierarchies). 

Each row must also define **exactly one** one of the following keys:

 - kanji - the row is a kanji definition, the row must be defined exactly once per unique ID
 - tango - the row carries a vocabulary entry for a kanji, e.g. there must exist a row with the same ID that has 'kanji' definition

> **SPARSE SUPPORT** Note: input supports many features like significance levels, formats.. but for output to truly respect
> given feature, it must implement its usage. That means you can for example use markdown or significance 
> level on a kanji 'imi' value, but it will not likely change anything in the output, since
> kanji packs nor PDFs nor any other output generator expects you to adjust kanji meaning with these.

### Minimal Example:
```
ID   1   kanji   思   　　　　 imi    myslet (emotivní)
ID   1   tango   思＜おも＞う  imi    myslet, věřit (něčemu)
```

### Key definitions - Data
Always, when some key is required, it can be present only once in the row. Optional keys can be present multiple times.
It is also not important what order the keys are defined in. With kanjis, ID rows must be unique. Each tango (word)
then uses the same ID as kanji it belongs to.

Dependening on the keys mentioned above, the row also can or must define other keys:
 - kanji
   - imi - **required**, the meaning of the kanji symbol
   - onyomi - the onyomi reading, optional, defined once per unique reading
   - kunyomi - the kunyomi reading, optional, defined once per unique reading
 - tango
   - imi - **required**, the meaning of the vocabulary entry
   - tsukaikata - an example usage sentence, optional
   - doushi - verb property, optional, useful for verb description:
     - supports one of: ``tadoushi`` (transitive), `jidoushi` (intransitive), `ichidan` (る-verb, 1 form) or `godan` (5 forms)
   - keiyoushi - adjective property, optional:
     - supports one of: ``na`` (na-adjective), `i` (i-adjective)  

You can also define arbitrary key-value pairs you wish, these will be included in 'other', 'notes' etc. sections.

#### Example:
```
ID     185      tango      思＜おも＞う       imi         myslet, věřit (něčemu)        doushi        godan        doushi     tadoushi         tsukaikata        そうだと思＜おも＞います。　Myslím, že je to tak.
-- OR --
ID     185      tango      思＜おも＞う       imi         myslet, věřit (něčemu)       tsukaikata        そうだと思＜おも＞います。　Myslím, že je to tak.         備<び>考<こう>      Jedná se o spíše 'emoční' než racionální myšlení.        tsukaikata        彼＜かれ＞のことをよく思＜おも＞っています。　Vážím si ho / Mám o něm vysoké mínění.
```
Both entries have different qualities. It is better to provide verb with information about its transitiveness and type.
The second example provides two usage examples to emphasise different use than in the 'to omou' grammar. Furthermore, it defines
custom **key** ``備<び>考<こう>`` which means 'note' and will be displayed in the 'extra' fields of the verb information section.

 ### Key definitions - Datasets

All datasets by default create learning content ``sets`` based on files they are stored in.
If you need to have two kanji order learning datasets, you can define the other one by using

 - setto
   - ids - **optional**, the ID set to compose a new dataset from, if missing
   it is the name of the dataset itself (see example)

Example:
````
ID    1   setto    My Awesome Dataset
ID    1   setto    1-20                     ids      184,181
````
Will create dataset _My Awesome Dataset_ with 1-20 kanji set name that contain two kanjis: 184 and 181.

It won't create a dataset by the file name
it occurs in. Rather, the dataset name comes from the value of the key `setto` and it defines
by ``ids`` what kanji IDs are to be included. These can be defined as `1,2,3,8,15` comma separated
list of **existing kanji** references.

### Key definitions - Metadata
``kanji`` and `tango` types are present in the _data_ used to generate output files. However, 
the app also supports arbitrary _metadata_. Each metadata row must be unique ID and type, there can
be two rows with the same ID if they differ in ``type``.

So, if you want to for example use radicals you can
define them in the very same way as you would other items, and if your desired generator
respects this metadata, it will be used along the data to enhance the outputs! Following
row keys - ``type``s - are supported:

 - radical
   - imi - **required**, the meaning of the kanji symbol
   - kunyomi
 

Unlike data, these metadata entries are available across all data items - they can be defined
once _anywhere_. We recommend therefore defining such data in separate sheets to not
to mix them with data entries - they will be later hard to find! KanTanJi can in this case
respect the type as a filename: if you do not put any _data_ rows in some file, such file
will not be treated as a daat source file, and thus it will not generate any direct outputs (pdf learning materials, anki decks...).

### Referencing Metadata
Any row can reference another row by the ``type`` and `ID` values. Referencing radical thus works
like key-value pair: ``ref`` - ``redical-3``, which says that given row references radical with ID 3.

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

## Formats
Data input is by default a plaintext intput. Keys can encode also format in case the value is not a plaintext.
The usage is: ``[format]key`` followed by `value` in the given format.
Supported formats are:
 - plaintext (default)
 - markdown ``[md]``

# Data Providers
The following data providers are supported. Some might need additional setup to use - they just provide
the data and might behave in very different ways.

## Google Sheets
To integrate wit google sheets and GitHub actions, you have to:

 - Create Project
 - Enable services: Goole Sheets API & Google Drive API
 - Create Service Account
 - Share the folder that hosts files with the target service account email

## Test Data
Test data is meant for testing. Such data is stored in ``/misc`` folder
and is used when no other source is configured. In that case, the application
does not overwrite any files it would normally generate (update README etc.), 
but creates only ``.test`` folder with test output & prints readme contents to stdout.

# Advanced: Writing New Data Source
To provide new data source, one must ensure that the data comes in tabular form 
described above. Such data must be then returned in the following dictionary (shown one entry,
all sheets must be attached like this):

````python
data_name = "name used for the output files, typicall range of kanji characters it provides info about"
output[data_name] = {
     "data": the_tabular_data,
     "id": the_unique_data_id_unchanged_even_when_data_name_changes,
     "name": data_name
}
````

# Advanced: Writing new Output Generator
Output generator needs to implement one function (`generate`):

````python
def generate(key, data, metadata, folder_getter):
    # First, check whether any data was modified, and if not, exit to spare resources
    data_modified = data["modified"]
    radicals = metadata.get["radical"] # Note that metadata is not guaranteed to be present, only if at least one radical entry was present in the data!
    radicals_set_modified = radicals is not None and radicals["modified"]
    
    if not data_modified or not radicals or not radicals_set_modified:
       return False
    
    # Use folder_getter to generate proper output location. In this folder, output a file suitable for your output type
    output_filename = f"{folder_getter(key)}/{key}.apkg"  # example for anki deck

    # Now, generate your output and store it in output_filename. You can also create multiple files if it is desirable.
    ...

    # Return True if files were created, False if nothing was generated for some reason
    return True
````
``folder_getter(key)`` is folder where all files of the same key (~dataset) remain.

Integration of this function is not yet automatic, therefore ``main.py`` must be modified
accordingly. This is going to be changed in the future.