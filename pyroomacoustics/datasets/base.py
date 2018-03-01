'''
Base class for some data corpus and the samples it contains.
The general idea is to create a sample object with an attribute
containing all metadata. Corpus objects that have a collection
of samples can then be created and can be filtered according
to the values in the metadata.

Example
-------

::

    # Prepare a few artificial samples
    samples = [
        {
            'data' : 0.99,
            'metadata' : { 'speaker' : 'alice', 'sex' : 'female', 'age' : 37, 'number' : 'one' },
        },
        {
            'data' : 2.1,
            'metadata' : { 'speaker' : 'alice', 'sex' : 'female', 'age' : 37, 'number' : 'two' },
        },
        {
            'data' : 1.02,
            'metadata' : { 'speaker' : 'bob', 'sex' : 'male', 'age' : 48, 'number' : 'one' },
        },
        {
            'data' : 2.07,
            'metadata' : { 'speaker' : 'bob', 'sex' : 'male', 'age' : 48, 'number' : 'two' },
        },
        ]

    corpus = CorpusBase()
    for s in samples:
        new_sample = SampleBase(s['data'], **s['metadata'])
        corpus.add_sample(new_sample)

    # Then, it possible to display summary info about the corpus
    print(corpus)

    # The number of samples in the corpus is given by ``len``
    print('Number of samples:', len(corpus))

    # And we can access samples with the slice operator
    print('Sample #2:')
    print(corpus[2])

    # We can obtain a new corpus with only male subject
    corpus_male_only = corpus.filter(sex='male')
    print(corpus_male_only)
  
'''

class Meta(object):
    '''
    A simple class that will take a dictionary as input
    and put the values in attributes named after the keys.
    We use it to store metadata for the samples

    The parameters can be any set of keyword arguments.
    They will all be transformed into attribute of the object.

    Methods:
    --------
    match:
        This method takes any number of keyword arguments
        and will return True if they all match exactly similarly
        named attributes of the object. If some keys are missing,
        an error will be raised. Omitted keys will be ignored.
    as_dict:
        Returns a dictionary representation of the object
    '''
    def __init__(self, **attr):
        for key, val in attr.items():
            self.__setattr__(key, val)

    def match(self, **kwargs):
        '''
        The key/value pairs given by the keyword arguments are compared
        to the attribute/value pairs of the object. If the values all
        match, True is returned. Otherwise False is returned. If a keyword
        argument has no attribute counterpart, an error is raised. Attributes
        that do not have a keyword argument counterpart are ignored.
        '''
        for key, val in kwargs.items():
            attr = self.__getattribute__(key)
            if attr != val and not (isinstance(val, list) and attr in val):
                return False
        return True

    def as_dict(self):
        ''' Returns all the attribute/value pairs of the object as a dictionary '''
        return self.__dict__.copy()

    def __str__(self):
        r = 'Metadata:\n'
        for attr, val in self.__dict__.items():
            r += '    {} : {}\n'.format(attr, val)
        return r[:-1]  # remove the trailing '\n'

    def __repr__(self):
        return self.__dict__.__repr__()


class SampleBase(object):
    '''
    The base class for a dataset sample. The idea is that different
    corpus will have different attributes for the samples. They
    should at least have a data attribute.

    Attributes
    ----------
    data: array_like
        The actual data
    meta: pyroomacoustics.datasets.Meta
        An object containing the sample metadata. They can be accessed using the
        dot operator
    '''

    def __init__(self, data, **kwargs):
        ''' Dummy init method '''
        self.data = data
        self.meta = Meta(**kwargs)

    def __str__(self):
        r = 'Data : ' + self.data.__str__() + '\n'
        r += self.meta.__str__()
        return r


class AudioSample(SampleBase):
    '''
    We add some methods specific to display and listen to audio samples.
    The sampling frequency of the samples is an extra parameter.

    For multichannel audio, we assume the same format used by 
    ```scipy.io.wavfile <https://docs.scipy.org/doc/scipy-0.14.0/reference/io.html#module-scipy.io.wavfile>`_``,
    that is ``data`` is then a 2D array with each column being a channel.

    Attributes
    ----------
    data: array_like
        The actual data
    fs: int
        The sampling frequency of the input signal
    meta: pyroomacoustics.datasets.Meta
        An object containing the sample metadata. They can be accessed using the
        dot operator
    '''
    def __init__(self, data, fs, **kwargs):
        SampleBase.__init__(self, data, **kwargs)
        self.fs = fs

    def play(self, **kwargs):
        '''
        Play the sound sample. This function uses the 
        ```sounddevice <https://python-sounddevice.readthedocs.io>`_`` package for playback.

        It takes the same keyword arguments as 
        ```sounddevice.play <https://python-sounddevice.readthedocs.io/en/0.3.10/#sounddevice.play>`_``.
        '''
        try:
            import sounddevice as sd
        except ImportError as e:
            print('Warning: sounddevice package is required to play audiofiles.')
            return

        sd.play(self.data, samplerate=self.fs, **kwargs)

    def plot(self, NFFT=512, noverlap=384, **kwargs):
        '''
        Plot the spectrogram of the audio sample. 

        It takes the same keyword arguments as ``matplotlib.pyplot.specgram``.
        '''

        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print('Warning: matplotlib is required for plotting')
            return

        # Handle single channel case
        if self.data.ndim == 1:
            data = self.data[:,None]

        nchannels = data.shape[1]

        # Try to have a square looking plot
        pcols = int(np.ceil(np.sqrt(nchannels)))
        prows = int(np.ceil(nchannels / pcols))

        for c in range(nchannels):
            plt.specgram(data[:,c], NFFT=NFFT, Fs=self.fs, noverlap=noverlap, **kwargs)
            plt.xlabel('Time [s]')
            plt.ylabel('Frequency [Hz]')
            plt.title('Channel {}'.format(c+1))


class CorpusBase(object):
    '''
    The base class for a data corpus. It has basically a list of
    samples and a filter function

    Attributes
    ----------
    samples: list
        A list of all the Samples in the dataset
    info: dict
        This dictionary keeps track of all the fields
        in the metadata. The keys of the dictionary are
        the metadata field names. The values are again dictionaries,
        but with the keys being the possible values taken by the 
        metadata and the associated value, the number of samples
        with this value in the corpus.
    '''
    def __init__(self):
        self.samples = []
        self.info = {}

    def add_sample(self, sample):
        ''' 
        Add a sample to the Corpus and keep track of the metadata.
        '''
        # keep track of the metadata going in the corpus
        for key, val in sample.meta.__dict__.items():
            if key not in self.info:
                self.info[key] = {}

            if val not in self.info[key]:
                self.info[key][val] = 1
            else:
                self.info[key][val] += 1

        # add the sample to the list
        self.samples.append(sample)

    def add_sample_matching(self, sample, **kwargs):
        '''
        The sample is added to the corpus only if all the keyword arguments
        match the metadata of the sample.  The match is operated by
        ``pyroomacoustics.datasets.Meta.match``.
        '''
        # check if the keyword arguments are matching
        if sample.meta.match(**kwargs):
            self.add_sample(sample)

    def filter(self, **kwargs):
        '''
        Filter the corpus and selects samples that match the criterias provided

        The criterias can be strings or list of strings, for the latter any string
        in the list is matched. If speakers are not specified, then all the speakers
        are used.
        '''

        new_corpus = CorpusBase()

        for s in self.samples:
            new_corpus.add_sample_matching(s, **kwargs)

        return new_corpus
        
    def __getitem__(self, r):
        return self.samples[r]

    def __len__(self):
        return len(self.samples)

    def __str__(self):
        r = 'The dataset contains {} samples.\n'.format(len(self))
        for field, values in self.info.items():
            r += '  {} ({}) :\n'.format(field, len(values))
            for value, number in values.items():
                r += '      * {} occurs {} times\n'.format(value, number)
        return r[:-1]  # remove trailing '\n'





