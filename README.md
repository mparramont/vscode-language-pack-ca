# Paquet d'idioma català per a VS Code

Traducció no oficial de la interfície de Visual Studio Code al català (valencià). Microsoft no publica cap paquet oficial en català, així que aquest paquet l'ha fet la comunitat.

Funciona a VS Code i als editors basats en VS Code, com ara Cursor i VSCodium.

## Agraïments

Aquest repositori és una bifurcació. Tota la feina de traducció revisada a mà és de les persones que el van començar:

- **[Aitor Gomila](https://github.com/aitor-gomila)** va crear el paquet i en va fer la primera traducció, publicada a [Open VSX](https://open-vsx.org/extension/AitorGomila/vscode-language-pack-ca).
- **[Poc Senderi](https://github.com/pocsenderi)** el va continuar a [pocsenderi/vscode-language-pack-ca](https://github.com/pocsenderi/vscode-language-pack-ca), va corregir-ne la traducció i el va publicar al [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=Katuak.vscode-language-pack-ca) com a Katuak.

Moltes gràcies a tots dos. Sense la seva feina, aquest paquet no existiria.

També en fem servir:

- Els traductors de [Softcatalà](https://www.softcatala.org/traductor/), el neuronal (anglès → català) i l'Apertium (castellà → català).
- El [paquet d'idioma castellà](https://marketplace.visualstudio.com/items?itemName=MS-CEINTL.vscode-language-pack-es) de Microsoft, amb llicència MIT, com a font de reserva.

## Què aporta aquesta bifurcació

El paquet original es va fer per a VS Code 1.80. Des d'aleshores, VS Code ha afegit milers de cadenes noves que apareixien en anglès. Aquesta versió les omple amb traducció automàtica:

| | Cadenes sense traduir a VS Code 1.139 |
|---|---|
| Versió 1.0.5 | 17.775 de 29.139 (61 %) |
| Versió 1.1.0 | 5 de 29.190 (0,02 %) |

D'aquestes cadenes noves, 17.784 venen del traductor neuronal i 11 de l'Apertium.

Les traduccions fetes a mà no s'han tocat. Les automàtiques estan llistades a [`traduccions-automatiques.json`](traduccions-automatiques.json), perquè sigui fàcil trobar-les i revisar-les. Sonaran estranyes de tant en tant: si en trobes una d'errònia, obre una incidència o una petició d'incorporació.

## Com s'instal·la

1. Instal·la el paquet des del [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=mparramon.vscode-language-pack-catala), o des de la terminal:

   ```
   code --install-extension mparramon.vscode-language-pack-catala
   ```

   Cursor no fa servir el Marketplace de Microsoft. Descarrega el `.vsix` de l'última [versió publicada](https://github.com/mparramont/vscode-language-pack-ca/releases) i instal·la'l amb `cursor --install-extension vscode-language-pack-catala-1.1.0.vsix`.

2. Obre la paleta d'ordres, executa **Configure Display Language** i tria **català**.
3. Reinicia l'editor.

## Com s'actualitza la traducció automàtica

Quan surt una versió nova de VS Code, torna a omplir les cadenes que falten:

1. Descarrega i descomprimeix l'última versió del paquet castellà de Microsoft.
2. Executa l'eina:

   ```
   uv run python eines/omple_traduccions.py \
       --vscode "/Applications/Visual Studio Code.app/Contents/Resources/app" \
       --castella ruta/al/vscode-language-pack-es/extension
   ```

L'eina només afegeix les cadenes que falten. Primer prova el traductor neuronal a partir de l'anglès. Si la traducció perd algun marcador, com ara `{0}`, codi entre accents greus o una icona `$(nom)`, prova l'Apertium a partir del castellà. Si tampoc no el conserva, deixa la cadena en anglès. Les traduccions es desen a `.cau/` perquè repetir l'execució no torni a demanar el que ja té.

## Com es genera el paquet

```
npm install --global @vscode/vsce
vsce package
```

El flux de treball de GitHub Actions fa el mateix a cada `push` a `main`, a cada etiqueta `v*` i a cada petició d'incorporació, i desa el `.vsix` com a artefacte. També es pot executar a mà des de la pestanya Actions.

## Llicència

[GPL 2.0](LICENSE), la mateixa que el projecte original.
