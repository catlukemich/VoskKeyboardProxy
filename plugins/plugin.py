import abc

class Plugin:
    '''
    Plugin base class (abstract)
    '''
    
    @abc.abstractmethod
    def requires_keyboard(self):
        '''
        Does the plugin require keyboard keys to be pressed to work?
        @return bool Does it? By default yes.
        '''
        return True
    
    @abc.abstractmethod
    def trigger_text(self):
        '''
        Text that triggers the pluggin to run.
        @return Should return array of strings.
        '''
        pass
    
    @abc.abstractmethod
    def execute_command(self, triggered_text):
        '''
        The commands that runs whe the command is triggered.
        @param receives that text that has triggered the plugin (from "trigger_text" method)
        '''
        pass