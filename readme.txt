
Asistente para la carga de ficheros CSV
========================================

Este script añade un asistente para la adición de ficheros CSV como tablas o capas a gvSIG desktop.


El asistente sustituye a la ventana que aparece al pulsar en el botón de propiedades en "añadir capa" o "añadir tabla".

Permite especificar entre otros:

- La configuración regional usada para interpretar fechas y números decimales.
- Si lleva o no cabecera.
- Separador de campos a utilizar.
- Tipos de los campos.
- Configuración del campo geometría si lo hubiese.
- Posición de las columnas para campos de tamaño fijo

Y previsualizar los datos antes de cargarlos como capa o tabla.


Instalación
=============

El script se entrega como un addon de gvSIG que puede ser instalado desde el administrador de complementos, indicando que deseamos instalar desde archivo y seleccionando el fichero.

Dependencias
==============

Precisa una versión de gvSIG desktop 2.3.0 build 2428 o superior, ya que se han corregido opciones en el driver de CSV para la correcta interpretación de los números con decimales, así como otras pequeñas correcciones.

