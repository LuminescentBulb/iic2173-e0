API: https://e0.stellux.org/history
IP: 184.192.89.203

Niveles de logro alcanzados:

- Requisitos Funcionales
    - RF1, RF3 y RF4 están en la misma función que permite filtrar y paginar
    - RF2 está en su propia función siguiendo la misma forma que la función de RF1, RF3 y RF4 sin la filtración ni la paginación

- Requisitos No Funcionales
    - RNF1 cumple todos los requisitos: persistir los eventos mediante llamadas POST y poder reconectarse sin intervención manual.
    - RNF2 está cumplido por la orquestación en docker-compose.yml
    - RNF3 y RNF5 están cumplidos en mi máquina EC2 con Nginx
    - RNF4 logrado con mi dominio e0.stellux.org
    - RNF6 logrado con el servicio de DB orquestado en docker-compose.yml
    - RNF7 logrado en el healthcheck de cada container en docker-compose.yml

- Docker Compose
    - RNF1, RNF2 y RNF3, todos incluidos en el docker-compose.yml

- HTTPS
    - RNF1, RNF2 y RNF3 logrados con certbot. Verificado al ir a http://e0.stellux.org/history, que redirige a https://e0.stellux.org/history

(Todo esto fue corregido gramaticalmente por IA con el prompt: “Corrige solo la gramática y no cambies ningún otro carácter”)
