import synthizer, random, math, time
import os 
from collections import OrderedDict


ctx = None
echo = None
reverb = None


buffer_cache = OrderedDict()
CACHE_MAXSIZE = 100

def initialize_context():
    global ctx, echo, reverb
    if ctx is None:
        ctx = synthizer.Context()
        echo = synthizer.GlobalEcho(ctx)  # Creiamo l'effetto echo una sola volta
        reverb = synthizer.GlobalFdnReverb(ctx)  # Inizializziamo il riverbero una sola volta

def get_buffer_from_cache(file):
    if file in buffer_cache:
        buffer_cache.move_to_end(file)  # Aggiorna come "più usato"
        return buffer_cache[file]
    # Caricamento buffer...
    buf = synthizer.Buffer.from_file(file)
    # Rimuovi il meno usato se la cache è piena
    if len(buffer_cache) >= CACHE_MAXSIZE:
        buffer_cache.popitem(last=False)
        del old_buf  # libera memoria
    buffer_cache[file] = buf
    return buf

class sound:
    def __init__(self, file, ctx=None):
        initialize_context()  # Ensure context is initialized
        self.ctx = ctx if ctx is not None else globals()['ctx']
        self.filepath = file   
        self.buffer = get_buffer_from_cache(file)
        self.source = synthizer.DirectSource(self.ctx)
        self.generator = None
        self.echo = None  # Inizializziamo l'effetto echo
        self.reverb = None  # Inizializziamo l'effetto di riverbero

    def play(self, looping=True, pitch=1.0, volume=1.0, rev=0.0, echo=False, etaps=20, edur=1, pitch_change=0):
        if self.generator is None:
            self.generator = synthizer.BufferGenerator(self.ctx)
            self.generator.buffer.value = self.buffer
            self.source.add_generator(self.generator)
            self.generator.looping.value = looping
            
            
            self.generator.pitch_bend.value = float(pitch)
            self.source.gain.value = float(volume)
        
        # Configuriamo l'effetto di riverbero, se necessario
        if rev > 0:
            if self.reverb is None:
                self.reverb = synthizer.GlobalFdnReverb(self.ctx)  # Inizializziamo il riverbero
            self.reverb.t60.value = float(rev)
            self.ctx.config_route(self.source, self.reverb)
        else:
            if self.reverb is not None:
                self.ctx.remove_route(self.source, self.reverb)

        if echo:
            self.echo = synthizer.GlobalEcho(self.ctx)  # Inizializziamo l'effetto echo
            self.set_echo_taps(etaps, edur)  # Configuriamo gli echo taps
            self.ctx.config_route(self.source, self.echo)  # Collega l'effetto echo alla sorgente

        if self.generator.playback_position.value >= self.buffer.get_length_in_seconds():
            self.generator.playback_position.value = float(0)

        # Controllo sul pitch in base alle posizioni di listener e source
        if hasattr(self, 'listener_y') and hasattr(self, 'source_y') and pitch_change==1:
            if self.source_y > self.listener_y:
                self.generator.pitch_bend.value = float(0.90)
            elif self.source_y < self.listener_y:
                self.generator.pitch_bend.value = float(1.05)
            elif self.source_y == self.listener_y:
                self.generator.pitch_bend.value = float(1.0)
        
        
    def pause(self):
        self.source.pause()


# Il metodo seek accetta valori positivi, per andare avanti di 1 o piu secondi o valori negativi per tornare indietro.

    def seek(self, seconds):
        current_position = self.generator.playback_position.value
        total_duration = self.buffer.get_length_in_seconds()
        new_position = current_position + seconds
        new_position = max(0, min(total_duration, new_position))
        self.generator.playback_position.value = float(new_position)
        time.sleep(0.1)  # Aspetta per dare il tempo al cambio di posizione di avere effetto
        print("Current Position:", self.generator.playback_position.value)
        print("Total Duration:", total_duration)

    def stop(self):
        if self.generator:
            self.source.remove_generator(self.generator)
            self.generator = None

    def set_echo_taps(self, etaps, edur):
        # Generate uniformly distributed random taps.
        n_taps = int(etaps)
        duration = edur
        delta = duration / n_taps
        taps = [
            synthizer.EchoTapConfig(
                float(delta + i * delta + random.random() * 0.01), float(random.random()), float(random.random())
            )
            for i in range(n_taps)
        ]

        # In general, you'll want to normalize by something, or otherwise work out how to prevent clipping.
        norm_left = sum([i.gain_l ** 2 for i in taps])
        norm_right = sum([i.gain_r ** 2 for i in taps])
        norm = 1.0 / math.sqrt(max(norm_left, norm_right))
        for t in taps:
            t.gain_l *= norm
            t.gain_r *= norm

        self.echo.set_taps(taps)
        self.ctx.config_route(self.source, self.echo)  # Collega l'effetto echo alla sorgente
    
    def set_lowpass(self, frequency, q=None):
        """Apply a lowpass filter to the source for occlusion or muffling effects."""
        if q is None:
            self.source.filter.value = synthizer.BiquadConfig.design_lowpass(frequency)
        else:
            self.source.filter.value = synthizer.BiquadConfig.design_lowpass(frequency, q)

    def set_highpass(self, frequency, q=None):
        """Apply a highpass filter to the source (e.g. simulate wall, pipe)."""
        if q is None:
            self.source.filter.value = synthizer.BiquadConfig.design_highpass(frequency)
        else:
            self.source.filter.value = synthizer.BiquadConfig.design_highpass(frequency, q)

    def set_bandpass(self, frequency, bandwidth):
        """Apply a bandpass filter to the source (e.g. simulate sound through pipe)."""
        self.source.filter.value = synthizer.BiquadConfig.design_bandpass(frequency, bandwidth)

    def clear_filter(self):
        """Remove any filter from the source."""
        self.source.filter.value = synthizer.BiquadConfig.design_identity()

    # ─── NUOVO METODO PER CAMBIARE IL VOLUME ─────────────────────────────────────
    def set_volume(self, volume: float):
        """
        Imposta (o aggiorna) il guadagno della sorgente audio.
        volume: valore float tra 0.0 e 1.0 (o oltre, se vuoi amplificare).
        """
        # Se la sorgente DirectSource è già stata creato (dopo play), basta modificare il guadagno:
        self.source.gain.value = float(volume)


class sound2d(sound):
    distanza_massima = 50
    instances = []

    def __init__(self, file, source_x=0, source_y=0, source_z=0, ctx=ctx, listener_x=0, listener_y=0, listener_z=0):
        super().__init__(file, ctx)
        self.source = synthizer.Source3D(self.ctx, synthizer.PannerStrategy.HRTF)
        self.source.distance_max.value = sound2d.distanza_massima

        # Listener position
        self.listener_x = listener_x
        self.listener_y = listener_y
        self.listener_z = listener_z
        self.ctx.position.value = [self.listener_x, self.listener_y, self.listener_z]

        # Source position
        self.source_x = source_x
        self.source_y = source_y
        self.source_z = source_z
        self.source.position.value = (self.source_x, self.source_y, self.source_z)
        sound2d.instances.append(self)

    def update_source(self, x, y, z=None):
        """Aggiorna la posizione della sorgente. z è opzionale (default: rimane quella corrente)."""
        if z is None:
            z = self.source_z
        self.source.position.value = (x, y, z)
        self.source_x = x
        self.source_y = y
        self.source_z = z

    def update_listener(self, x, y, z=None):
        """Aggiorna la posizione del listener. z è opzionale (default: rimane quella corrente)."""
        if z is None:
            z = self.listener_z
        self.ctx.position.value = (x, y, z)
        self.listener_x = x
        self.listener_y = y
        self.listener_z = z

    def play(self, looping=True, pitch=1.0, volume=1.0, rev=0.0, echo=False, etaps=20, edur=1, pitch_change=1):
        if self.generator is None:
            self.generator = synthizer.BufferGenerator(self.ctx)
            self.generator.buffer.value = self.buffer
            self.source.add_generator(self.generator)
            self.generator.looping.value = looping
            
            
            self.generator.pitch_bend.value = float(pitch)
            self.source.gain.value = float(volume)

        # Riverbero
        if rev > 0:
            if self.reverb is None:
                self.reverb = synthizer.GlobalFdnReverb(self.ctx)
            self.reverb.t60.value = float(rev)
            self.ctx.config_route(self.source, self.reverb)
        else:
            if self.reverb is not None:
                self.ctx.remove_route(self.source, self.reverb)

        # Echo
        if echo:
            self.echo = synthizer.GlobalEcho(self.ctx)
            self.set_echo_taps(etaps, edur)
            self.ctx.config_route(self.source, self.echo)

        if self.generator.playback_position.value >= self.buffer.get_length_in_seconds():
            self.generator.playback_position.value = float(0)

        # Pitch change (y-axis)
        if hasattr(self, 'listener_y') and hasattr(self, 'source_y') and pitch_change == 1:
            if self.source_y > self.listener_y:
                self.generator.pitch_bend.value = float(0.90)
            elif self.source_y < self.listener_y:
                self.generator.pitch_bend.value = float(1.05)
            elif self.source_y == self.listener_y:
                self.generator.pitch_bend.value = float(1.0)
        
    @classmethod
    def imposta_distanza(cls, value):
        cls.distanza_massima = value
        for instance in cls.instances:
            instance.source.distance_max.value = value
            instance.play()

    @classmethod
    def imposta_modello_distanza(cls, value):
        cls.distance_model = value
        for instance in cls.instances:
            instance.ctx.distance_model = value

class Sound3D(sound):
    max_distance = 50
    instances = []

    def __init__(self, file, source_x=0, source_y=0, source_z=0, ctx=ctx, listener_x=0, listener_y=0, listener_z=0):
        super().__init__(file, ctx)
        self.source = synthizer.Source3D(self.ctx, synthizer.PannerStrategy.HRTF)
        self.source.distance_max.value = Sound3D.max_distance
        self.listener_x = listener_x
        self.listener_y = listener_y
        self.listener_z = listener_z
        self.ctx.position.value = [self.listener_x, self.listener_y, self.listener_z]
        self.source_x = source_x
        self.source_y = source_y
        self.source_z = source_z
        self.source.position.value = (self.source_x, self.source_y, self.source_z)
        Sound3D.instances.append(self)

    def update_source(self, x, y, z):
        """Update the position of the sound source in 3D."""
        self.source.position.value = (x, y, z)
        self.source_x = x
        self.source_y = y
        self.source_z = z

    def update_listener(self, x, y, z):
        """Update the position of the listener in 3D."""
        self.ctx.position.value = (x, y, z)
        self.listener_x = x
        self.listener_y = y
        self.listener_z = z

    @classmethod
    def set_max_distance(cls, value):
        cls.max_distance = value
        for instance in cls.instances:
            instance.source.distance_max.value = value
            instance.play()

    @classmethod
    def set_distance_model(cls, value):
        cls.distance_model = value
        for instance in cls.instances:
            instance.ctx.distance_model = value

