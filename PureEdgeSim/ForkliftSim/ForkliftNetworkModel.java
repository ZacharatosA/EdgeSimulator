package ForkliftSim;

import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode;
import com.mechalikh.pureedgesim.network.DefaultNetworkModel;
import com.mechalikh.pureedgesim.network.NetworkLink;
import com.mechalikh.pureedgesim.network.TransferProgress;
import com.mechalikh.pureedgesim.simulationmanager.SimulationManager;
import com.mechalikh.pureedgesim.scenariomanager.SimulationParameters.TYPES;
import com.mechalikh.pureedgesim.datacentersmanager.ComputingNode.LinkOrientation;
import com.mechalikh.pureedgesim.taskgenerator.Task;

import java.util.ArrayList;
import java.util.List;

public class ForkliftNetworkModel extends DefaultNetworkModel {

    public ForkliftNetworkModel(SimulationManager simulationManager) {
        super(simulationManager);
    }

    @Override
    public void send(ComputingNode from, ComputingNode to, Task task, double fileSize, TransferProgress.Type type) {
        // Ειδικός χειρισμός για forklift -> GNB επικοινωνία
        if (isForkliftToGnbCommunication(from, to)) {
            handleForkliftToGnbTransfer(from, to, task, fileSize, type);
        }
        // Ειδικός χειρισμός για GNB -> forklift επικοινωνία
        else if (isGnbToForkliftCommunication(from, to)) {
            handleGnbToForkliftTransfer(from, to, task, fileSize, type);
        }
        // Για όλες τις άλλες περιπτώσεις, χρησιμοποιούμε την προεπιλεγμένη υλοποίηση
        else {
            super.send(from, to, task, fileSize, type);
        }
    }

    private boolean isForkliftToGnbCommunication(ComputingNode from, ComputingNode to) {
        return from.getType() == TYPES.EDGE_DEVICE && to.getType() == TYPES.EDGE_DATACENTER;
    }

    private boolean isGnbToForkliftCommunication(ComputingNode from, ComputingNode to) {
        return from.getType() == TYPES.EDGE_DATACENTER && to.getType() == TYPES.EDGE_DEVICE;
    }

    private void handleForkliftToGnbTransfer(ComputingNode from, ComputingNode to, Task task, double fileSize, TransferProgress.Type type) {
        // Λίστα για κομβους        
        List<ComputingNode> vertexList = new ArrayList<>();
        // Λίστα για σύνδεση
        List<NetworkLink> edgeList = new ArrayList<>();
        
        // Απευθείας σύνδεση forklift -> GNB
        vertexList.addAll(List.of(from, to));
        edgeList.add(from.getCurrentLink(LinkOrientation.UP_LINK));
        
        startTransfer(edgeList, vertexList, task, fileSize, type);
    }

    private void handleGnbToForkliftTransfer(ComputingNode from, ComputingNode to, Task task, double fileSize, TransferProgress.Type type) {
        List<ComputingNode> vertexList = new ArrayList<>();
        List<NetworkLink> edgeList = new ArrayList<>();
        
        // Απευθείας σύνδεση GNB -> forklift
        vertexList.addAll(List.of(from, to));
        edgeList.add(to.getCurrentLink(LinkOrientation.DOWN_LINK));
        
        startTransfer(edgeList, vertexList, task, fileSize, type);
    }

    private void startTransfer(List<NetworkLink> edgeList, List<ComputingNode> vertexList, Task task, double fileSize, TransferProgress.Type type) {
        if (!edgeList.isEmpty()) {
            edgeList.get(0).addTransfer(
                new TransferProgress(task, fileSize, type)
                    .setVertexList(vertexList)
                    .setEdgeList(edgeList));
        }
    }
} 